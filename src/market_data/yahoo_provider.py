from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import sys

import pandas as pd
import yfinance as yf

from src.config import load_instruments


@dataclass(frozen=True)
class PricePoint:
    # timestamp_utc is the time at which the OHLC close is actually available,
    # not merely the bar-start label returned by Yahoo.
    timestamp_utc: str
    bar_start_utc: str
    available_at_utc: str
    interval_minutes: int
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
    out = out.sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out.columns = [str(c).lower().replace(" ", "_") for c in out.columns]
    return out


def _set_interval_minutes(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    out = df.copy()
    out.attrs["interval_minutes"] = int(minutes)
    return out


def interval_minutes(df: pd.DataFrame) -> int:
    try:
        value = int(df.attrs.get("interval_minutes", 1))
    except (TypeError, ValueError):
        value = 1
    return max(1, value)


def bar_available_at_index(df: pd.DataFrame) -> pd.DatetimeIndex:
    """Return the time each OHLC bar is complete/usable.

    Yahoo labels intraday bars by bar START. A 10:15 1m close is not known at
    10:15:30; it becomes available at 10:16. All pre-decision calculations must
    therefore filter on this derived availability time.
    """
    minutes = interval_minutes(df)
    return df.index + pd.Timedelta(minutes=minutes)


def completed_bars_at_or_before(df: pd.DataFrame, when_utc: datetime) -> pd.DataFrame:
    if df.empty:
        return df
    when_utc = _ensure_utc(when_utc)
    mask = bar_available_at_index(df) <= pd.Timestamp(when_utc)
    out = df.loc[mask].copy()
    out.attrs.update(df.attrs)
    return out


def bars_available_between(
    df: pd.DataFrame,
    start_utc: datetime,
    end_utc: datetime,
    *,
    include_start: bool = False,
) -> pd.DataFrame:
    if df.empty:
        return df
    start_utc = _ensure_utc(start_utc)
    end_utc = _ensure_utc(end_utc)
    available = bar_available_at_index(df)
    start_ts = pd.Timestamp(start_utc)
    end_ts = pd.Timestamp(end_utc)
    if include_start:
        mask = (available >= start_ts) & (available <= end_ts)
    else:
        mask = (available > start_ts) & (available <= end_ts)
    out = df.loc[mask].copy()
    out.attrs.update(df.attrs)
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

    return _set_interval_minutes(_normalize_frame(df), 1)


def _point_from_row(df: pd.DataFrame, position: int) -> PricePoint:
    ts = df.index[position].to_pydatetime().astimezone(timezone.utc)
    minutes = interval_minutes(df)
    available = ts + timedelta(minutes=minutes)
    row = df.iloc[position]
    return PricePoint(
        timestamp_utc=available.isoformat(),
        bar_start_utc=ts.isoformat(),
        available_at_utc=available.isoformat(),
        interval_minutes=minutes,
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
    )


def last_complete_bar_before(df: pd.DataFrame, event_time_utc: datetime) -> PricePoint | None:
    """Last bar whose close was available by decision time.

    This intentionally does NOT use the most recent bar-start label. It filters
    by bar_end/available_at to prevent look-ahead leakage from an unfinished bar.
    """
    if df.empty:
        return None
    completed = completed_bars_at_or_before(df, event_time_utc)
    if completed.empty:
        return None
    return _point_from_row(completed, len(completed) - 1)


def first_complete_bar_at_or_after(df: pd.DataFrame, target_time_utc: datetime) -> PricePoint | None:
    """First close that is actually available at or after a target timestamp."""
    if df.empty:
        return None
    target_time_utc = _ensure_utc(target_time_utc)
    available = bar_available_at_index(df)
    positions = [i for i, ts in enumerate(available) if ts >= pd.Timestamp(target_time_utc)]
    if not positions:
        return None
    return _point_from_row(df, positions[0])


def first_bar_at_or_after(df: pd.DataFrame, target_time_utc: datetime) -> PricePoint | None:
    """Backward-compatible name with corrected complete-bar semantics."""
    return first_complete_bar_at_or_after(df, target_time_utc)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m src.market_data.yahoo_provider XAUUSD")
        return 2

    instrument = sys.argv[1].upper()
    now = datetime.now(timezone.utc)
    frame = fetch_1m_window(instrument, now, before_minutes=60, after_minutes=1)
    point = last_complete_bar_before(frame, now)
    if point is None:
        print(f"No recent complete 1m data returned for {instrument}")
        return 1

    print(
        f"{instrument}: {point.close} available={point.available_at_utc} "
        f"bar_start={point.bar_start_utc} source={point.source}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
