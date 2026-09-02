from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yaml
import yfinance as yf

from src.config import ROOT

CONFIG_PATH = ROOT / "config" / "market_context.yaml"


def _parse_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = out.columns.get_level_values(0)
    out.columns = [str(c).lower().replace(" ", "_") for c in out.columns]
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    return out


def _last_close_before(df: pd.DataFrame, when: datetime) -> tuple[str, float] | None:
    if df.empty:
        return None
    eligible = df[df.index < pd.Timestamp(when)]
    if eligible.empty:
        return None
    ts = eligible.index[-1]
    close = float(eligible.iloc[-1]["close"])
    return ts.to_pydatetime().astimezone(timezone.utc).isoformat(), close


def _change_pct(start: float | None, end: float | None) -> float | None:
    if start is None or end is None or start == 0:
        return None
    return ((end - start) / start) * 100.0


def _change_abs(start: float | None, end: float | None) -> float | None:
    if start is None or end is None:
        return None
    return end - start


def _trend_label(name: str, value: float | None, change_pct_60m: float | None, change_abs_60m: float | None, config: dict) -> str:
    if value is None:
        return "UNKNOWN"

    regimes = config.get("regimes", {})
    if name == "VIX":
        vix_cfg = regimes.get("VIX", {})
        if value >= float(vix_cfg.get("high_at_or_above", 25.0)):
            return "HIGH"
        if value < float(vix_cfg.get("low_below", 18.0)):
            return "LOW"
        return "ELEVATED"

    item_cfg = regimes.get(name, {})
    if name in {"US2Y", "US10Y"}:
        threshold = float(item_cfg.get("trend_threshold_abs_60m", 0.03))
        if change_abs_60m is None:
            return "UNKNOWN"
        if change_abs_60m >= threshold:
            return "RISING"
        if change_abs_60m <= -threshold:
            return "FALLING"
        return "FLAT"

    threshold = float(item_cfg.get("trend_threshold_pct_60m", 0.15))
    if change_pct_60m is None:
        return "UNKNOWN"
    if change_pct_60m >= threshold:
        return "RISING"
    if change_pct_60m <= -threshold:
        return "FALLING"
    return "FLAT"


def fetch_pre_event_context(event_time_utc: datetime) -> dict:
    """Capture market context using only bars strictly before the event time."""
    event_time_utc = _parse_utc(event_time_utc)
    config = _load_config()
    lookbacks = config.get("lookbacks_minutes", {})
    short_minutes = int(lookbacks.get("short", 60))
    long_minutes = int(lookbacks.get("long", 240))
    start = event_time_utc - timedelta(minutes=long_minutes + 30)
    end = event_time_utc + timedelta(minutes=1)

    series_out: dict[str, dict] = {}
    labels: dict[str, str] = {}

    for name, meta in config.get("context_series", {}).items():
        symbol = meta["yahoo_symbol"]
        try:
            frame = yf.download(
                symbol,
                start=start,
                end=end,
                interval="1m",
                progress=False,
                auto_adjust=False,
                prepost=True,
                threads=False,
            )
            frame = _normalize(frame)
            current = _last_close_before(frame, event_time_utc)
            short = _last_close_before(frame, event_time_utc - timedelta(minutes=short_minutes))
            long = _last_close_before(frame, event_time_utc - timedelta(minutes=long_minutes))

            value = None if current is None else current[1]
            short_value = None if short is None else short[1]
            long_value = None if long is None else long[1]
            change_pct_60m = _change_pct(short_value, value)
            change_pct_240m = _change_pct(long_value, value)
            change_abs_60m = _change_abs(short_value, value)

            label = _trend_label(name, value, change_pct_60m, change_abs_60m, config)
            labels[name] = label
            series_out[name] = {
                "symbol": symbol,
                "source": "yahoo",
                "value": value,
                "timestamp_utc": None if current is None else current[0],
                "change_pct_60m": None if change_pct_60m is None else round(change_pct_60m, 6),
                "change_pct_240m": None if change_pct_240m is None else round(change_pct_240m, 6),
                "change_abs_60m": None if change_abs_60m is None else round(change_abs_60m, 6),
                "regime": label,
            }
        except Exception as exc:
            labels[name] = "UNKNOWN"
            series_out[name] = {
                "symbol": symbol,
                "source": "yahoo",
                "value": None,
                "timestamp_utc": None,
                "regime": "UNKNOWN",
                "error": f"{type(exc).__name__}: {exc}",
            }

    return {
        "captured_for_event_time_utc": event_time_utc.isoformat(),
        "information_cutoff": "strictly_before_event",
        "source": "yahoo",
        "series": series_out,
        "regimes": labels,
    }


def context_signature(snapshot: dict | None) -> str:
    if not snapshot:
        return "NO_CONTEXT"
    regimes = snapshot.get("regimes", {})
    order = ("DXY", "US2Y", "US10Y", "VIX", "WTI", "BRENT")
    return "|".join(f"{name}={regimes.get(name, 'UNKNOWN')}" for name in order)
