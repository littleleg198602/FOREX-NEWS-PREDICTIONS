from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import sys

import pandas as pd
import yfinance as yf

from src.config import load_instruments


@dataclass(frozen=True)
class PricePoint:
    timestamp_utc: str
    open: float
    high: float
    low: float
    close: float
    source: str = "yahoo"


def _ensure_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    out.columns = [str(c).lower().replace(" ", "_") for c in out.columns]
    return out


def fetch_1m_window(instrument: str, event_time_utc: datetime, before_minutes: int = 30, after_minutes: int = 300) -> pd.DataFrame:
    instruments = load_instruments()
    if instrument not in instruments:
        raise KeyError(f"Unknown instrument: {instrument}")

    symbol = instruments[instrument]["yahoo_symbol"]
    event_time_utc = _ensure_utc(event_time_utc)
    start = event_time_utc - timedelta(minutes=before_minutes)
    end = event_time_utc + timedelta(minutes=after_minutes + 2)

    df = yf.download(
        symbol,
        start=start,
        end=end,
        interval="1m",
        progress=False,
        auto_adjust=False,
        prepost=True,
        threads=False,
    )

    if isinstance(df.columns, pd.MultiIndex):
        # yfinance may return a ticker level even for one symbol.
        df.columns = df.columns.get_level_values(0)

    return _normalize_frame(df)


def last_complete_bar_before(df: pd.DataFrame, event_time_utc: datetime) -> PricePoint | None:
    if df.empty:
        return None
    event_time_utc = _ensure_utc(event_time_utc)
    eligible = df[df.index < pd.Timestamp(event_time_utc)]
    if eligible.empty:
        return None
    ts = eligible.index[-1]
    row = eligible.iloc[-1]
    return PricePoint(
        timestamp_utc=ts.to_pydatetime().astimezone(timezone.utc).isoformat(),
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
    )


def first_bar_at_or_after(df: pd.DataFrame, target_time_utc: datetime) -> PricePoint | None:
    if df.empty:
        return None
    target_time_utc = _ensure_utc(target_time_utc)
    eligible = df[df.index >= pd.Timestamp(target_time_utc)]
    if eligible.empty:
        return None
    ts = eligible.index[0]
    row = eligible.iloc[0]
    return PricePoint(
        timestamp_utc=ts.to_pydatetime().astimezone(timezone.utc).isoformat(),
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
    )


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m src.market_data.yahoo_provider XAUUSD")
        return 2

    instrument = sys.argv[1].upper()
    now = datetime.now(timezone.utc)
    frame = fetch_1m_window(instrument, now, before_minutes=60, after_minutes=1)
    point = last_complete_bar_before(frame, now)
    if point is None:
        print(f"No recent 1m data returned for {instrument}")
        return 1

    print(f"{instrument}: {point.close} @ {point.timestamp_utc} source={point.source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
