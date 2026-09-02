from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

import pandas as pd

from src.config import ROOT, load_evaluation_config
from src.market_data.yahoo_provider import fetch_1m_window, last_complete_bar_before, first_bar_at_or_after


def _parse_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _pct_change(start: float, end: float) -> float:
    return ((end - start) / start) * 100.0


def _actual_direction(change_pct: float, epsilon: float = 1e-12) -> str:
    if change_pct > epsilon:
        return "UP"
    if change_pct < -epsilon:
        return "DOWN"
    return "FLAT"


def _direction_correct(predicted: str, actual: str) -> bool | None:
    predicted = predicted.upper()
    if predicted in {"UP", "DOWN"}:
        return predicted == actual
    # MIXED/VOLATILITY require dedicated scoring rules, so MVP leaves them unscored.
    return None


def _mfe_mae(frame: pd.DataFrame, ref_time: datetime, target_time: datetime, ref_price: float, predicted: str) -> tuple[float | None, float | None]:
    window = frame[(frame.index > pd.Timestamp(ref_time)) & (frame.index <= pd.Timestamp(target_time))]
    if window.empty or predicted not in {"UP", "DOWN"}:
        return None, None

    highs = ((_safe_series(window, "high") - ref_price) / ref_price) * 100.0
    lows = ((_safe_series(window, "low") - ref_price) / ref_price) * 100.0

    if predicted == "UP":
        return float(highs.max()), float(lows.min())
    return float(-lows.min()), float(-highs.max())


def _safe_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        raise KeyError(f"Missing OHLC column: {column}")
    return frame[column].astype(float)


def evaluate_one_instrument(prediction_id: str, event_time: datetime, item: dict) -> dict:
    instrument = item["instrument"]
    predicted_immediate = item["immediate"]["direction"].upper()

    frame = fetch_1m_window(instrument, event_time, before_minutes=60, after_minutes=300)
    ref = last_complete_bar_before(frame, event_time)
    if ref is None:
        return {
            "prediction_id": prediction_id,
            "instrument": instrument,
            "status": "NO_REFERENCE_PRICE",
            "market_data_source": "yahoo",
        }

    ref_time = _parse_utc(ref.timestamp_utc)
    result = {
        "prediction_id": prediction_id,
        "instrument": instrument,
        "status": "PARTIAL",
        "market_data_source": "yahoo",
        "reference_price": ref.close,
        "reference_price_time_utc": ref.timestamp_utc,
        "predicted_immediate_direction": predicted_immediate,
        "evaluations": {},
    }

    horizons = {"15m": 15, "1h": 60, "4h": 240}
    completed = 0
    now = datetime.now(timezone.utc)

    for horizon_id, minutes in horizons.items():
        target = event_time + timedelta(minutes=minutes)
        if now < target:
            result["evaluations"][horizon_id] = {"status": "PENDING"}
            continue

        point = first_bar_at_or_after(frame, target)
        if point is None:
            result["evaluations"][horizon_id] = {
                "status": "NO_TRADED_PRICE",
                "target_time_utc": target.isoformat(),
            }
            continue

        actual_change = _pct_change(ref.close, point.close)
        actual_direction = _actual_direction(actual_change)
        mfe, mae = _mfe_mae(frame, ref_time, _parse_utc(point.timestamp_utc), ref.close, predicted_immediate)

        result["evaluations"][horizon_id] = {
            "status": "DONE",
            "target_time_utc": target.isoformat(),
            "actual_price_time_utc": point.timestamp_utc,
            "price": point.close,
            "change_pct": round(actual_change, 6),
            "actual_direction": actual_direction,
            "correct": _direction_correct(predicted_immediate, actual_direction),
            "mfe_pct": None if mfe is None else round(mfe, 6),
            "mae_pct": None if mae is None else round(mae, 6),
        }
        completed += 1

    result["evaluations"]["next_session"] = {
        "status": "NOT_IMPLEMENTED",
        "note": "Requires exchange-calendar aware session logic; planned for next phase."
    }

    if completed == len(horizons):
        result["status"] = "DONE"
    return result


def evaluate_prediction(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        prediction = json.load(f)

    event_time = _parse_utc(prediction["created_at_utc"])
    prediction_id = prediction["prediction_id"]

    return {
        "prediction_id": prediction_id,
        "event_id": prediction.get("event_id"),
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_version": prediction.get("model_version"),
        "results": [
            evaluate_one_instrument(prediction_id, event_time, item)
            for item in prediction.get("predictions", [])
        ],
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python -m src.evaluation.evaluate_prediction data/predictions/example.json")
        return 2

    src_path = Path(sys.argv[1])
    output = evaluate_prediction(src_path)

    out_dir = ROOT / "data" / "evaluations"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{output['prediction_id']}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
