from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

import pandas as pd

from src.config import ROOT, load_instruments
from src.market_data.context_snapshot import fetch_pre_event_context
from src.market_data.yahoo_provider import fetch_1m_window, last_complete_bar_before, first_bar_at_or_after

VOLATILITY_RATIO_THRESHOLD = 1.25
MAX_MARKET_WINDOW_MINUTES = 4 * 24 * 60
SESSION_IDLE_COMPLETE_MINUTES = 90


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


def _baseline_range_pct(frame: pd.DataFrame, decision_time: datetime, minutes: int, ref_price: float) -> float | None:
    start = decision_time - timedelta(minutes=minutes)
    pre = frame[(frame.index >= pd.Timestamp(start)) & (frame.index < pd.Timestamp(decision_time))]
    baseline = _range_pct(pre, ref_price)

    # Around closed markets a clock-time window can contain no bars or only a
    # single stale bar, producing a zero range. Fall back to recent traded bars
    # so MIXED/VOLATILITY are not judged against a meaningless zero envelope.
    if len(pre) < 2 or baseline is None or baseline <= 0:
        fallback = frame[frame.index < pd.Timestamp(decision_time)].tail(max(60, minutes))
        baseline = _range_pct(fallback, ref_price)

    if baseline is None or baseline <= 0:
        return None
    return baseline


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
        if baseline_range_pct is None or baseline_range_pct <= 0:
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


def _decision_time(event_time: datetime, created_at_value: str | None) -> tuple[datetime, datetime | None, float | None]:
    if not created_at_value:
        return event_time, None, None
    created_at = _parse_utc(created_at_value)
    anchor = max(event_time, created_at)
    latency = max(0.0, (created_at - event_time).total_seconds())
    return anchor, created_at, latency


def _forward_minutes(decision_time: datetime, now: datetime) -> int:
    elapsed = max(0, int((now - decision_time).total_seconds() // 60))
    return min(MAX_MARKET_WINDOW_MINUTES, max(300, elapsed + 30))


def _local_dates(frame: pd.DataFrame, timezone_name: str) -> pd.Series:
    local_index = frame.index.tz_convert(ZoneInfo(timezone_name))
    return pd.Series([ts.date() for ts in local_index], index=frame.index)


def _next_session_frame(
    frame: pd.DataFrame,
    instrument: str,
    decision_time: datetime,
    now: datetime,
) -> tuple[str, pd.DataFrame | None, date | None]:
    if frame.empty:
        return "PENDING", None, None

    instruments = load_instruments()
    timezone_name = instruments[instrument].get("timezone", "UTC")
    tz = ZoneInfo(timezone_name)
    local_dates = _local_dates(frame, timezone_name)
    decision_local_date = decision_time.astimezone(tz).date()

    before_decision_same_day = frame[
        (local_dates == decision_local_date) & (frame.index < pd.Timestamp(decision_time))
    ]

    dates_after_decision = sorted(
        {
            d
            for ts, d in local_dates.items()
            if ts >= pd.Timestamp(decision_time)
            and (d > decision_local_date if not before_decision_same_day.empty else d >= decision_local_date)
        }
    )
    if not dates_after_decision:
        return "PENDING", None, None

    session_date = dates_after_decision[0]
    session = frame[local_dates == session_date]
    if session.empty:
        return "PENDING", None, session_date

    later_session_exists = any(d > session_date for d in set(local_dates.tolist()))
    last_bar_utc = session.index[-1].to_pydatetime().astimezone(timezone.utc)
    now_local_date = now.astimezone(tz).date()
    idle_minutes = (now - last_bar_utc).total_seconds() / 60.0
    complete = (
        later_session_exists
        or now_local_date > session_date
        or (now_local_date == session_date and idle_minutes >= SESSION_IDLE_COMPLETE_MINUTES)
    )
    return ("DONE" if complete else "PENDING"), session, session_date


def _evaluate_next_session(
    frame: pd.DataFrame,
    instrument: str,
    decision_time: datetime,
    ref_time: datetime,
    ref_price: float,
    item: dict,
    now: datetime,
) -> dict:
    predicted = item.get("next_session", {}).get("direction")
    if not predicted:
        return {"status": "NOT_PREDICTED"}
    predicted = str(predicted).upper()

    status, session, session_date = _next_session_frame(frame, instrument, decision_time, now)
    if status != "DONE" or session is None or session.empty:
        return {
            "status": status,
            "session_local_date": None if session_date is None else session_date.isoformat(),
            "predicted_direction": predicted,
        }

    point_ts = session.index[-1].to_pydatetime().astimezone(timezone.utc)
    point_price = float(session.iloc[-1]["close"])
    actual_change = _pct_change(ref_price, point_price)
    actual_direction = _actual_direction(actual_change)
    baseline = _baseline_range_pct(frame, decision_time, 240, ref_price)
    post_range = _range_pct(session, ref_price)
    score = _score_non_directional(predicted, actual_change, post_range, baseline)
    mfe, mae = _mfe_mae(frame, ref_time, point_ts, ref_price, predicted)

    return {
        "status": "DONE",
        "session_local_date": session_date.isoformat(),
        "actual_price_time_utc": point_ts.isoformat(),
        "price": point_price,
        "change_pct": round(actual_change, 6),
        "actual_direction": actual_direction,
        "predicted_direction": predicted,
        "predicted_confidence": item.get("next_session", {}).get("confidence"),
        "correct": score.get("correct"),
        "score_type": score.get("score_type"),
        "baseline_range_pct": None if baseline is None else round(baseline, 6),
        "post_event_range_pct": None if post_range is None else round(post_range, 6),
        "mfe_pct": None if mfe is None else round(mfe, 6),
        "mae_pct": None if mae is None else round(mae, 6),
        "evaluation_method": "last_bar_of_next_relevant_local_trading_date",
        **{k: v for k, v in score.items() if k not in {"correct", "score_type"}},
    }


def evaluate_one_instrument(prediction_id: str, decision_time: datetime, item: dict) -> dict:
    instrument = item["instrument"]
    predicted_immediate = item["immediate"]["direction"].upper()
    now = datetime.now(timezone.utc)

    frame = fetch_1m_window(
        instrument,
        decision_time,
        before_minutes=MAX_MARKET_WINDOW_MINUTES,
        after_minutes=_forward_minutes(decision_time, now),
    )
    ref = last_complete_bar_before(frame, decision_time)
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
        "reference_rule": "last_traded_bar_before_prediction_decision",
        "predicted_immediate_direction": predicted_immediate,
        "predicted_confidence": item.get("immediate", {}).get("confidence"),
        "evaluations": {},
    }

    horizons = {"15m": 15, "1h": 60, "4h": 240}
    for horizon_id, minutes in horizons.items():
        target = decision_time + timedelta(minutes=minutes)
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

        post = _window(frame, decision_time, actual_point_time, include_start=True)
        post_range_pct = _range_pct(post, ref.close)
        baseline_range_pct = _baseline_range_pct(frame, decision_time, minutes, ref.close)
        score = _score_non_directional(predicted_immediate, actual_change, post_range_pct, baseline_range_pct)

        result["evaluations"][horizon_id] = {
            "status": "DONE",
            "target_time_utc": target.isoformat(),
            "actual_price_time_utc": point.timestamp_utc,
            "market_delay_minutes": round(max(0.0, (actual_point_time - target).total_seconds() / 60.0), 2),
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

    result["evaluations"]["next_session"] = _evaluate_next_session(
        frame,
        instrument,
        decision_time,
        ref_time,
        ref.close,
        item,
        now,
    )

    statuses = [entry.get("status") for entry in result["evaluations"].values()]
    if statuses and all(status == "DONE" for status in statuses):
        result["status"] = "DONE"
    elif any(status == "DONE" for status in statuses):
        result["status"] = "PARTIAL"
    else:
        result["status"] = "PENDING"
    return result


def evaluate_prediction(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        prediction = json.load(f)

    event_time_value = prediction.get("event_time_utc") or prediction.get("published_at_utc")
    if not event_time_value:
        raise ValueError(f"Prediction {prediction.get('prediction_id', path.name)} has no event_time_utc/published_at_utc")

    event_time = _parse_utc(event_time_value)
    decision_time, created_at, latency = _decision_time(event_time, prediction.get("created_at_utc"))
    prediction_id = prediction["prediction_id"]

    stored_context = prediction.get("market_context_at_prediction")
    if stored_context:
        market_context = stored_context
        context_origin = "captured_at_prediction"
    else:
        market_context = fetch_pre_event_context(decision_time)
        context_origin = "reconstructed_pre_decision_from_yahoo"

    return {
        "prediction_id": prediction_id,
        "event_id": prediction.get("event_id"),
        "event_time_utc": event_time.isoformat(),
        "prediction_time_utc": None if created_at is None else created_at.isoformat(),
        "evaluation_anchor_time_utc": decision_time.isoformat(),
        "prediction_latency_seconds": None if latency is None else round(latency, 3),
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_version": prediction.get("model_version"),
        "is_example": bool(prediction.get("is_example", False)),
        "backfilled": bool(prediction.get("backfilled", False)),
        "eligible_for_hit_rate": bool(prediction.get("eligible_for_hit_rate", True)) and not bool(prediction.get("is_example", False)),
        "market_context_origin": context_origin,
        "market_context": market_context,
        "results": [
            evaluate_one_instrument(prediction_id, decision_time, item)
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
