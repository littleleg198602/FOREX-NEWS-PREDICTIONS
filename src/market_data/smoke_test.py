from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

import pandas as pd
import yaml
import yfinance as yf

from src.config import ROOT, load_instruments
from src.market_data.context_snapshot import _candidate_list
from src.market_data.yahoo_provider import _normalize_frame, last_complete_bar_before, first_bar_at_or_after

REQUIRED_COLUMNS = {"open", "high", "low", "close"}
HORIZONS = {"15m": 15, "1h": 60, "4h": 240}


def _download_recent(symbol: str, interval: str = "1m") -> pd.DataFrame:
    df = yf.download(
        symbol,
        period="5d",
        interval=interval,
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
        return False, "no data"
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


def _load_context_config() -> dict:
    with (ROOT / "config" / "market_context.yaml").open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _test_context_candidates() -> int:
    config = _load_context_config()
    failures = 0
    print("\n=== Yahoo market-context smoke test ===")

    for name, meta in config.get("context_series", {}).items():
        candidate_errors: list[str] = []
        passed = False
        for candidate in _candidate_list(meta):
            symbol = candidate.get("symbol")
            if not symbol:
                continue
            for interval in ("1m", "5m"):
                try:
                    frame = _download_recent(symbol, interval=interval)
                    ok, detail = _validate_frame(frame)
                    if ok:
                        proxy = f" proxy_for={candidate.get('proxy_for')}" if candidate.get("proxy_for") else ""
                        inverse = " inverse=true" if candidate.get("inverse_to_role") else ""
                        print(f"[OK] {name:<7} {symbol:<12} {interval:<3} {detail}{proxy}{inverse}")
                        passed = True
                        break
                    candidate_errors.append(f"{symbol}/{interval}: {detail}")
                except Exception as exc:
                    candidate_errors.append(f"{symbol}/{interval}: {type(exc).__name__}: {exc}")
            if passed:
                break

        if not passed:
            print(f"[FAIL] {name:<7} no usable candidate; {'; '.join(candidate_errors)}")
            failures += 1
    return failures


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
        except Exception as exc:
            print(f"[FAIL] {instrument:<8} {symbol:<12} {type(exc).__name__}: {exc}")
            failures += 1

    print("\n=== End-to-end calculation test ===")
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

    failures += _test_context_candidates()

    print("\n=== Result ===")
    if failures:
        print(f"FAILED: {failures} problem(s) detected")
        return 1

    print("PASSED: tracked instruments and all market-context series have usable Yahoo data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
