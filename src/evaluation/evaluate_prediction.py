from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

import pandas as pd

from src.config import ROOT
from src.market_data.context_snapshot import fetch_pre_event_context
from src.market_data.yahoo_provider import fetch_1m_window, last_complete_bar_before, first_bar_at_or_after

VOLATILITY_RATIO_THRESHOLD = 1.25


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
    return None


def _safe_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        raise KeyError(f"Missing OHLC column: {column}")
    return frame[column].astype(float)


def _range_pct(frame: pd.DataFrame, ref_price: float) -> float | None:
    if frame.empty or ref_price == 0:
        return None
    high = float(_safe_series(frame, "high").max())
    low = float(_safe_series(frame, "low").min())
    return ((high - low) / ref_price) * 100.0


def _window(frame: pd.DataFrame, start: datetime, end: datetime, include_start: bool = False) -> pd.DataFrame:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if include_start:
        return frame[(frame.index >= start_ts) & (frame.index <= end_ts)]
    return frame[(frame.index > start_ts) & (frame.index <= end_ts)]


def _baseline_range_pct(frame: pd.DataFrame, event_time: datetime, minutes: int, ref_price: float) -> float | None:
    start = event_time - timedelta(minutes=minutes)
    pre = frame[(frame.index >= pd.Timestamp(start)) & (frame.index < pd.Timestamp(event_time))]
    return _range_pct(pre, ref_price)


def _mfe_mae(frame: pd.DataFrame, ref_time: datetime, target_time: datetime, ref_price: float, predicted: str) -> tuple[float | None, float | None]:
    window = frame[(frame.index > pd.Timestamp(ref_time)) & (frame.index <= pd.Timestamp(target_time))]
    if window.empty or predicted not in {"UP", "DOWN"}:
        return None, None

    highs = ((_safe_series(window, "high") - ref_price) / ref_price) * 100.0
    lows = ((_safe_series(window, "low") - ref_price) / ref_price) * 100.0

    if predicted == "UP":
        return float(highs.max()), float(lows.min())
    return float(-lows.min()), float(-highs.max())


def _score_non_directional(predicted: str, change_pct: float, post_range_pct: float | None, baseline_range_pct: float | None) -> dict:
    predicted = predicted.upper()

    if predicted == "VOLATILITY":
        if post_range_pct is None or baseline_range_pct is None or baseline_range_pct <= 0:
            return {
                "score_type": "volatility",
                "correct": None,
                "volatility_ratio": None,
            }
        ratio = post_range_pct / baseline_range_pct
        return {
            "score_type": "volatility",
            "correct": ratio >= VOLATILITY_RATIO_THRESHOLD,
            "volatility_ratio": round(ratio, 6),
            "volatility_ratio_threshold": VOLATILITY_RATIO_THRESHOLD,
        }

    if predicted == "MIXED":
        if baseline_range_pct is None:
            return {
                "score_type": "mixed_neutral",
                "correct": None,
                "neutral_envelope_pct": None,
            }
        envelope = baseline_range_pct
        return {
            "score_type": "mixed_neutral",
            "correct": abs(change_pct) <= envelope,
            "neutral_envelope_pct": round(envelope, 6),
        }

    return {
        "score_type": "directional",
        "correct": _direction_correct(predicted, _actual_direction(change_pct)),
    }


def evaluate_one_instrument(prediction_id: str, event_time: datetime, item: dict) -> dict:
    instrument = item["instrument"]
    predicted_immediate = item["immediate"]["direction"].upper()

    frame = fetch_1m_window(instrument, event_time, before_minutes=240, after_minutes=300)
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
        "predicted_confidence": item.get("immediate", {}).get("confidence"),
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
        actual_point_time = _parse_utc(point.timestamp_utc)
        mfe, mae = _mfe_mae(frame, ref_time, actual_point_time, ref.close, predicted_immediate)

        post = _window(frame, event_time, actual_point_time, include_start=True)
        post_range_pct = _range_pct(post, ref.close)
        baseline_range_pct = _baseline_range_pct(frame, event_time, minutes, ref.close)
        score = _score_non_directional(predicted_immediate, actual_change, post_range_pct, baseline_range_pct)

        result["evaluations"][horizon_id] = {
            "status": "DONE",
            "target_time_utc": target.isoformat(),
            "actual_price_time_utc": point.timestamp_utc,
            "price": point.close,
            "change_pct": round(actual_change, 6),
            "actual_direction": actual_direction,
            "correct": score.get("correct"),
            "score_type": score.get("score_type"),
            "baseline_range_pct": None if baseline_range_pct is None else round(baseline_range_pct, 6),
            "post_event_range_pct": None if post_range_pct is None else round(post_range_pct, 6),
            "mfe_pct": None if mfe is None else round(mfe, 6),
            "mae_pct": None if mae is None else round(mae, 6),
            **{k: v for k, v in score.items() if k not in {"correct", "score_type"}},
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

    event_time_value = prediction.get("event_time_utc") or prediction.get("published_at_utc")
    if not event_time_value:
        raise ValueError(f"Prediction {prediction.get('prediction_id', path.name)} has no event_time_utc/published_at_utc")

    event_time = _parse_utc(event_time_value)
    prediction_id = prediction["prediction_id"]

    stored_context = prediction.get("market_context_at_prediction")
    if stored_context:
        market_context = stored_context
        context_origin = "captured_at_prediction"
    else:
        market_context = fetch_pre_event_context(event_time)
        context_origin = "reconstructed_pre_event_from_yahoo"

    return {
        "prediction_id": prediction_id,
        "event_id": prediction.get("event_id"),
        "event_time_utc": event_time.isoformat(),
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_version": prediction.get("model_version"),
        "backfilled": bool(prediction.get("backfilled", False)),
        "eligible_for_hit_rate": bool(prediction.get("eligible_for_hit_rate", True)),
        "market_context_origin": context_origin,
        "market_context": market_context,
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
