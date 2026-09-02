from __future__ import annotations

from datetime import datetime, timedelta, timezone

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


def _last_close_before(df: pd.DataFrame, when: datetime) -> tuple[datetime, float] | None:
    if df.empty:
        return None
    eligible = df[df.index < pd.Timestamp(when)]
    if eligible.empty:
        return None
    ts = eligible.index[-1].to_pydatetime().astimezone(timezone.utc)
    close = float(eligible.iloc[-1]["close"])
    return ts, close


def _change_pct(start: float | None, end: float | None) -> float | None:
    if start is None or end is None or start == 0:
        return None
    return ((end - start) / start) * 100.0


def _change_abs(start: float | None, end: float | None) -> float | None:
    if start is None or end is None:
        return None
    return end - start


def _trend_label(
    name: str,
    value: float | None,
    change_pct_60m: float | None,
    change_abs_60m: float | None,
    config: dict,
    trend_metric: str | None = None,
) -> str:
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
    if name in {"US2Y", "US10Y"} and trend_metric != "pct":
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


def _candidate_list(meta: dict) -> list[dict]:
    candidates = meta.get("candidates")
    if candidates:
        return [dict(item) for item in candidates]
    symbol = meta.get("yahoo_symbol")
    return [{"symbol": symbol}] if symbol else []


def _download(symbol: str, start: datetime, end: datetime, interval: str) -> pd.DataFrame:
    frame = yf.download(
        symbol,
        start=start,
        end=end,
        interval=interval,
        progress=False,
        auto_adjust=False,
        prepost=True,
        threads=False,
    )
    return _normalize(frame)


def _candidate_snapshot(
    name: str,
    meta: dict,
    candidate: dict,
    decision_time_utc: datetime,
    config: dict,
) -> dict | None:
    lookbacks = config.get("lookbacks_minutes", {})
    short_minutes = int(lookbacks.get("short", 60))
    long_minutes = int(lookbacks.get("long", 240))
    history_minutes = int(lookbacks.get("history", max(long_minutes + 30, 5760)))
    start = decision_time_utc - timedelta(minutes=history_minutes)
    end = decision_time_utc + timedelta(minutes=1)
    symbol = candidate["symbol"]

    last_error: Exception | None = None
    selected_interval: str | None = None
    frame = pd.DataFrame()
    for interval in ("1m", "5m"):
        try:
            frame = _download(symbol, start, end, interval)
            if not frame.empty and "close" in frame.columns:
                selected_interval = interval
                break
        except Exception as exc:
            last_error = exc
            frame = pd.DataFrame()

    if frame.empty or selected_interval is None:
        if last_error:
            raise last_error
        return None

    current = _last_close_before(frame, decision_time_utc)
    if current is None:
        return None

    short = _last_close_before(frame, decision_time_utc - timedelta(minutes=short_minutes))
    long = _last_close_before(frame, decision_time_utc - timedelta(minutes=long_minutes))

    current_ts, value = current
    short_value = None if short is None else short[1]
    long_value = None if long is None else long[1]

    raw_change_pct_60m = _change_pct(short_value, value)
    raw_change_pct_240m = _change_pct(long_value, value)
    raw_change_abs_60m = _change_abs(short_value, value)

    inverse = bool(candidate.get("inverse_to_role", meta.get("inverse_to_role", False)))
    sign = -1.0 if inverse else 1.0
    change_pct_60m = None if raw_change_pct_60m is None else raw_change_pct_60m * sign
    change_pct_240m = None if raw_change_pct_240m is None else raw_change_pct_240m * sign
    change_abs_60m = None if raw_change_abs_60m is None else raw_change_abs_60m * sign

    age_minutes = max(0.0, (decision_time_utc - current_ts).total_seconds() / 60.0)
    freshness_cfg = config.get("freshness", {})
    max_staleness = float(
        meta.get(
            "max_staleness_minutes",
            freshness_cfg.get("default_max_staleness_minutes", 180),
        )
    )
    is_fresh = age_minutes <= max_staleness
    trend_metric = candidate.get("trend_metric", meta.get("trend_metric"))

    label = _trend_label(name, value, change_pct_60m, change_abs_60m, config, trend_metric)
    if not is_fresh and name != "VIX":
        label = "UNKNOWN"

    return {
        "symbol": symbol,
        "source": "yahoo",
        "interval": selected_interval,
        "value": value,
        "timestamp_utc": current_ts.isoformat(),
        "age_minutes": round(age_minutes, 2),
        "fresh": is_fresh,
        "max_staleness_minutes": max_staleness,
        "proxy_for": candidate.get("proxy_for", meta.get("proxy_for")),
        "inverse_to_role": inverse,
        "trend_metric": trend_metric,
        "change_pct_60m": None if change_pct_60m is None else round(change_pct_60m, 6),
        "change_pct_240m": None if change_pct_240m is None else round(change_pct_240m, 6),
        "change_abs_60m": None if change_abs_60m is None else round(change_abs_60m, 6),
        "raw_change_pct_60m": None if raw_change_pct_60m is None else round(raw_change_pct_60m, 6),
        "raw_change_abs_60m": None if raw_change_abs_60m is None else round(raw_change_abs_60m, 6),
        "regime": label,
    }


def fetch_pre_event_context(event_time_utc: datetime) -> dict:
    """Capture context strictly before the supplied prediction/decision timestamp."""
    decision_time_utc = _parse_utc(event_time_utc)
    config = _load_config()

    series_out: dict[str, dict] = {}
    labels: dict[str, str] = {}

    for name, meta in config.get("context_series", {}).items():
        snapshots: list[dict] = []
        errors: list[str] = []
        for candidate in _candidate_list(meta):
            symbol = candidate.get("symbol")
            if not symbol:
                continue
            try:
                snapshot = _candidate_snapshot(name, meta, candidate, decision_time_utc, config)
                if snapshot:
                    snapshots.append(snapshot)
                    if snapshot.get("fresh"):
                        break
            except Exception as exc:
                errors.append(f"{symbol}: {type(exc).__name__}: {exc}")

        if snapshots:
            fresh = [item for item in snapshots if item.get("fresh")]
            selected = fresh[0] if fresh else min(snapshots, key=lambda item: item.get("age_minutes", 1e12))
            if not selected.get("fresh") and name != "VIX":
                selected["regime"] = "UNKNOWN"
            labels[name] = selected.get("regime", "UNKNOWN")
            if errors:
                selected["candidate_errors"] = errors
            series_out[name] = selected
        else:
            labels[name] = "UNKNOWN"
            series_out[name] = {
                "source": "yahoo",
                "value": None,
                "timestamp_utc": None,
                "regime": "UNKNOWN",
                "candidate_errors": errors or ["No usable Yahoo candidate"],
            }

    return {
        "captured_for_time_utc": decision_time_utc.isoformat(),
        "captured_for_event_time_utc": decision_time_utc.isoformat(),
        "information_cutoff": "strictly_before_prediction_decision_time",
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
