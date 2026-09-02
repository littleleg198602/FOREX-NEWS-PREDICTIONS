from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
import sys

import pandas as pd
import yfinance as yf

from src.config import load_instruments
from src.market_data.yahoo_provider import _normalize_frame, last_complete_bar_before, first_bar_at_or_after

REQUIRED_COLUMNS = {"open", "high", "low", "close"}
HORIZONS = {"15m": 15, "1h": 60, "4h": 240}


def _download_recent(symbol: str) -> pd.DataFrame:
    df = yf.download(
        symbol,
        period="5d",
        interval="1m",
        progress=False,
        auto_adjust=False,
        prepost=True,
        threads=False,
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return _normalize_frame(df)


def _validate_frame(df: pd.DataFrame) -> tuple[bool, str]:
    if df.empty:
        return False, "no 1m data"
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        return False, f"missing columns: {sorted(missing)}"
    if not isinstance(df.index, pd.DatetimeIndex):
        return False, "index is not DatetimeIndex"
    if df.index.tz is None:
        return False, "timestamps are not timezone-aware"
    numeric = df[["open", "high", "low", "close"]].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().all().any():
        return False, "OHLC contains unusable values"
    if (numeric["high"] < numeric["low"]).any():
        return False, "high < low detected"
    return True, f"{len(df)} bars, latest={df.index[-1].isoformat()}"


def _pct(start: float, end: float) -> float:
    return ((end - start) / start) * 100.0


def _pick_event_time(df: pd.DataFrame) -> datetime | None:
    if len(df) < 300:
        return None

    # Prefer a timestamp with enough actual bars after it. This avoids picking a point
    # at the very end of the data set and makes the test independent of current time.
    for idx in range(len(df) - 241, 60, -1):
        ts = df.index[idx]
        later = df[df.index >= ts + pd.Timedelta(minutes=240)]
        earlier = df[df.index < ts]
        if not earlier.empty and not later.empty:
            return ts.to_pydatetime().astimezone(timezone.utc)
    return None


def _end_to_end_check(instrument: str, df: pd.DataFrame) -> tuple[bool, str]:
    event_time = _pick_event_time(df)
    if event_time is None:
        return False, "not enough suitable data for E2E horizons"

    ref = last_complete_bar_before(df, event_time)
    if ref is None or not math.isfinite(ref.close) or ref.close <= 0:
        return False, "reference price unavailable"

    parts: list[str] = []
    for name, minutes in HORIZONS.items():
        target = event_time + timedelta(minutes=minutes)
        point = first_bar_at_or_after(df, target)
        if point is None:
            return False, f"{name}: no traded price"
        move = _pct(ref.close, point.close)
        if not math.isfinite(move):
            return False, f"{name}: invalid percentage move"
        parts.append(f"{name}={move:+.3f}%")

    return True, f"ref={ref.close:.4f}; " + ", ".join(parts)


def main() -> int:
    instruments = load_instruments()
    failures = 0

    print("\n=== Yahoo 1m market-data smoke test ===")
    print(f"UTC now: {datetime.now(timezone.utc).isoformat()}")
    print(f"Instruments: {len(instruments)}\n")

    frames: dict[str, pd.DataFrame] = {}

    for instrument, cfg in instruments.items():
        symbol = cfg.get("yahoo_symbol")
        if not symbol:
            print(f"[FAIL] {instrument:<8} no yahoo_symbol configured")
            failures += 1
            continue

        try:
            frame = _download_recent(symbol)
            frames[instrument] = frame
            ok, detail = _validate_frame(frame)
            status = "OK" if ok else "FAIL"
            print(f"[{status}] {instrument:<8} {symbol:<12} {detail}")
            if not ok:
                failures += 1
        except Exception as exc:  # network/provider errors must be visible in Actions log
            print(f"[FAIL] {instrument:<8} {symbol:<12} {type(exc).__name__}: {exc}")
            failures += 1

    print("\n=== End-to-end calculation test ===")
    # Use XAUUSD first because it trades nearly continuously. If unavailable, try any
    # instrument that passed the data test.
    ordered = ["XAUUSD"] + [x for x in instruments if x != "XAUUSD"]
    e2e_done = False
    for instrument in ordered:
        frame = frames.get(instrument)
        if frame is None or frame.empty:
            continue
        ok, detail = _end_to_end_check(instrument, frame)
        if ok:
            print(f"[OK] {instrument}: {detail}")
            e2e_done = True
            break
        print(f"[SKIP] {instrument}: {detail}")

    if not e2e_done:
        print("[FAIL] No instrument had enough data for the end-to-end test")
        failures += 1

    print("\n=== Result ===")
    if failures:
        print(f"FAILED: {failures} problem(s) detected")
        return 1

    print("PASSED: all configured Yahoo symbols returned usable 1m data and E2E calculation worked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
