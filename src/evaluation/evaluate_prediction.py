from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

import pandas as pd

from src.config import ROOT, load_evaluation_config, load_instruments
from src.market_data.context_snapshot import fetch_pre_event_context
from src.market_data.yahoo_provider import (
    bar_available_at_index,
    bars_available_between,
    completed_bars_at_or_before,
    fetch_1m_window,
    first_complete_bar_at_or_after,
    last_complete_bar_before,
)
from src.prediction.normalization import (
    normalize_market_context,
    normalize_prediction,
    validate_normalized_prediction,
)

EVAL_CONFIG = load_evaluation_config()
EVALUATION_VERSION = str(EVAL_CONFIG.get("evaluation_version", "2.0.0"))
FIXED_HORIZONS = {
    item["id"]: int(item["minutes"])
    for item in EVAL_CONFIG.get("evaluation_horizons", [])
    if item.get("minutes") is not None
}
VOLATILITY_RATIO_THRESHOLD = float(
    EVAL_CONFIG.get("classification", {}).get("volatility_ratio_threshold", 1.25)
)
REFERENCE_MAX_AGE_MINUTES = float(
    EVAL_CONFIG.get("reference_price", {}).get("reference_max_age_minutes_for_fixed_horizons", 10)
)
MAX_MARKET_DELAY_MINUTES = float(
    EVAL_CONFIG.get("fixed_horizon_quality", {}).get("max_market_delay_minutes", 5)
)
MAX_MARKET_WINDOW_MINUTES = 7 * 24 * 60
TERMINAL_STATUSES = {
    "DONE",
    "NOT_PREDICTED",
    "MARKET_CLOSED",
    "DATA_GAP",
    "NO_REFERENCE_PRICE",
}


def _parse_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _config_hash() -> str:
    payload = {
        "evaluation": EVAL_CONFIG,
        "instruments": load_instruments(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _pct_change(start: float, end: float) -> float:
    return ((end - start) / start) * 100.0


def _direction_threshold_pct(baseline_range_pct: float | None) -> float:
    cfg = EVAL_CONFIG.get("classification", {}).get("directional_threshold", {})
    floor = float(cfg.get("absolute_floor_pct", 0.01))
    fraction = float(cfg.get("fraction", 0.10))
    if baseline_range_pct is None or baseline_range_pct <= 0:
        return floor
    return max(floor, baseline_range_pct * fraction)


def _actual_direction(change_pct: float, threshold_pct: float = 0.0) -> str:
    threshold = max(0.0, float(threshold_pct))
    if change_pct > threshold:
        return "UP"
    if change_pct < -threshold:
        return "DOWN"
    return "NO_MOVE"


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
    return bars_available_between(frame, start, end, include_start=include_start)


def _baseline_range_pct(frame: pd.DataFrame, decision_time: datetime, minutes: int, ref_price: float) -> float | None:
    completed = completed_bars_at_or_before(frame, decision_time)
    if completed.empty:
        return None

    start = decision_time - timedelta(minutes=minutes)
    available = bar_available_at_index(completed)
    pre = completed.loc[
        (available >= pd.Timestamp(start)) & (available <= pd.Timestamp(decision_time))
    ].copy()
    pre.attrs.update(completed.attrs)
    baseline = _range_pct(pre, ref_price)

    # If the exact clock-time baseline contains too few traded bars, use the
    # most recent completed traded bars only. This never includes a post-decision
    # candle because `completed` is already availability-filtered.
    if len(pre) < 2 or baseline is None or baseline <= 0:
        fallback = completed.tail(max(60, minutes)).copy()
        fallback.attrs.update(completed.attrs)
        baseline = _range_pct(fallback, ref_price)

    if baseline is None or baseline <= 0:
        return None
    return baseline


def _mfe_mae(
    frame: pd.DataFrame,
    ref_time: datetime,
    target_time: datetime,
    ref_price: float,
    predicted: str,
) -> tuple[float | None, float | None]:
    window = bars_available_between(frame, ref_time, target_time, include_start=False)
    if window.empty or predicted not in {"UP", "DOWN"}:
        return None, None

    highs = ((_safe_series(window, "high") - ref_price) / ref_price) * 100.0
    lows = ((_safe_series(window, "low") - ref_price) / ref_price) * 100.0

    if predicted == "UP":
        return float(highs.max()), float(lows.min())
    return float(-lows.min()), float(-highs.max())


def _score_non_directional(
    predicted: str,
    change_pct: float,
    post_range_pct: float | None,
    baseline_range_pct: float | None,
    directional_threshold_pct: float = 0.0,
) -> dict:
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

    actual = _actual_direction(change_pct, directional_threshold_pct)
    return {
        "score_type": "directional",
        "correct": _direction_correct(predicted, actual),
        "directional_threshold_pct": round(directional_threshold_pct, 6),
        "actual_direction_thresholded": actual,
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
    return min(MAX_MARKET_WINDOW_MINUTES, max(300, elapsed + 60))


def _local_dates(frame: pd.DataFrame, timezone_name: str) -> pd.Series:
    local_index = frame.index.tz_convert(ZoneInfo(timezone_name))
    return pd.Series([ts.date() for ts in local_index], index=frame.index)


def _next_session_frame(
    frame: pd.DataFrame,
    instrument: str,
    decision_time: datetime,
    now: datetime,
) -> tuple[str, pd.DataFrame | None, date | None]:
    del now  # Session completion is confirmed by later traded data, not silence.
    if frame.empty:
        return "PENDING", None, None

    instruments = load_instruments()
    timezone_name = instruments[instrument].get("timezone", "UTC")
    tz = ZoneInfo(timezone_name)
    local_dates = _local_dates(frame, timezone_name)
    decision_local_date = decision_time.astimezone(tz).date()

    available = bar_available_at_index(frame)
    before_decision_same_day = frame.loc[
        (local_dates == decision_local_date) & (available <= pd.Timestamp(decision_time))
    ]

    dates_after_decision = sorted(
        {
            d
            for available_ts, d in zip(available, local_dates.tolist())
            if available_ts >= pd.Timestamp(decision_time)
            and (d > decision_local_date if not before_decision_same_day.empty else d >= decision_local_date)
        }
    )
    if not dates_after_decision:
        return "PENDING", None, None

    session_date = dates_after_decision[0]
    session = frame.loc[local_dates == session_date].copy()
    session.attrs.update(frame.attrs)
    if session.empty:
        return "PENDING", None, session_date

    # Conservative close confirmation: a session becomes DONE only after at
    # least one bar from a later local trading date is observed. Feed silence
    # during an open session can therefore never masquerade as a close.
    later_session_exists = any(d > session_date for d in set(local_dates.tolist()))
    return ("DONE" if later_session_exists else "PENDING"), session, session_date


def _previous_session_frame(frame: pd.DataFrame, instrument: str, session_date: date) -> pd.DataFrame | None:
    if frame.empty:
        return None
    instruments = load_instruments()
    timezone_name = instruments[instrument].get("timezone", "UTC")
    local_dates = _local_dates(frame, timezone_name)
    previous_dates = sorted({d for d in local_dates.tolist() if d < session_date})
    if not previous_dates:
        return None
    previous = frame.loc[local_dates == previous_dates[-1]].copy()
    previous.attrs.update(frame.attrs)
    return previous if not previous.empty else None


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

    point = last_complete_bar_before(session, datetime.now(timezone.utc))
    if point is None:
        return {"status": "PENDING", "session_local_date": session_date.isoformat(), "predicted_direction": predicted}
    point_ts = _parse_utc(point.available_at_utc)
    point_price = point.close
    actual_change = _pct_change(ref_price, point_price)

    previous_session = _previous_session_frame(frame, instrument, session_date)
    previous_session_range = None if previous_session is None else _range_pct(previous_session, ref_price)
    post_range = _range_pct(session, ref_price)
    directional_threshold = _direction_threshold_pct(previous_session_range)
    actual_direction = _actual_direction(actual_change, directional_threshold)
    score = _score_non_directional(
        predicted,
        actual_change,
        post_range,
        previous_session_range,
        directional_threshold,
    )
    mfe, mae = _mfe_mae(frame, ref_time, point_ts, ref_price, predicted)

    return {
        "status": "DONE",
        "session_local_date": session_date.isoformat(),
        "actual_price_time_utc": point.available_at_utc,
        "actual_price_bar_start_utc": point.bar_start_utc,
        "price": point_price,
        "change_pct": round(actual_change, 6),
        "actual_direction": actual_direction,
        "predicted_direction": predicted,
        "predicted_confidence": item.get("next_session", {}).get("confidence"),
        "correct": score.get("correct"),
        "score_type": score.get("score_type"),
        "baseline_range_pct": None if previous_session_range is None else round(previous_session_range, 6),
        "baseline_definition": "previous_relevant_local_trading_session_range",
        "post_event_range_pct": None if post_range is None else round(post_range, 6),
        "mfe_pct": None if mfe is None else round(mfe, 6),
        "mae_pct": None if mae is None else round(mae, 6),
        "evaluation_method": "last_complete_bar_of_next_relevant_local_trading_date_confirmed_by_later_trading_date",
        **{k: v for k, v in score.items() if k not in {"correct", "score_type"}},
    }


def evaluate_one_instrument(prediction_id: str, decision_time: datetime, item: dict) -> dict:
    instrument = item["instrument"]
    predicted_immediate = str(item["immediate"]["direction"]).upper()
    now = datetime.now(timezone.utc)
    instrument_cfg = load_instruments().get(instrument, {})

    try:
        frame = fetch_1m_window(
            instrument,
            decision_time,
            before_minutes=MAX_MARKET_WINDOW_MINUTES,
            after_minutes=_forward_minutes(decision_time, now),
        )
    except Exception as exc:
        return {
            "prediction_id": prediction_id,
            "instrument": instrument,
            "status": "PROVIDER_ERROR",
            "market_data_source": "yahoo",
            "provider_error": f"{type(exc).__name__}: {exc}",
            "evaluations": {},
        }

    ref = last_complete_bar_before(frame, decision_time)
    if ref is None:
        return {
            "prediction_id": prediction_id,
            "instrument": instrument,
            "status": "NO_REFERENCE_PRICE",
            "market_data_source": "yahoo",
            "yahoo_symbol": instrument_cfg.get("yahoo_symbol"),
            "evaluations": {
                horizon: {"status": "NO_REFERENCE_PRICE"} for horizon in FIXED_HORIZONS
            } | {"next_session": {"status": "NO_REFERENCE_PRICE"}},
        }

    ref_time = _parse_utc(ref.available_at_utc)
    reference_age_minutes = max(0.0, (decision_time - ref_time).total_seconds() / 60.0)
    result = {
        "prediction_id": prediction_id,
        "instrument": instrument,
        "status": "PARTIAL",
        "market_data_source": "yahoo",
        "yahoo_symbol": instrument_cfg.get("yahoo_symbol"),
        "yahoo_proxy_for": instrument_cfg.get("yahoo_proxy_for"),
        "yahoo_proxy_type": instrument_cfg.get("yahoo_proxy_type"),
        "reference_price": ref.close,
        "reference_price_time_utc": ref.available_at_utc,
        "reference_price_bar_start_utc": ref.bar_start_utc,
        "reference_bar_interval_minutes": ref.interval_minutes,
        "reference_age_minutes": round(reference_age_minutes, 3),
        "reference_rule": "last_bar_whose_close_was_available_at_or_before_prediction_decision",
        "predicted_immediate_direction": predicted_immediate,
        "predicted_confidence": item.get("immediate", {}).get("confidence"),
        "evaluations": {},
    }

    for horizon_id, minutes in FIXED_HORIZONS.items():
        target = decision_time + timedelta(minutes=minutes)
        if now < target:
            result["evaluations"][horizon_id] = {"status": "PENDING", "target_time_utc": target.isoformat()}
            continue

        if reference_age_minutes > REFERENCE_MAX_AGE_MINUTES:
            result["evaluations"][horizon_id] = {
                "status": "MARKET_CLOSED",
                "target_time_utc": target.isoformat(),
                "reason": "reference price was stale at decision time; fixed clock-time reaction is not scoreable",
                "reference_age_minutes": round(reference_age_minutes, 3),
            }
            continue

        point = first_complete_bar_at_or_after(frame, target)
        if point is None:
            result["evaluations"][horizon_id] = {
                "status": "DATA_GAP",
                "target_time_utc": target.isoformat(),
                "reason": "no complete traded bar available at/after target",
            }
            continue

        actual_point_time = _parse_utc(point.available_at_utc)
        market_delay_minutes = max(0.0, (actual_point_time - target).total_seconds() / 60.0)
        if market_delay_minutes > MAX_MARKET_DELAY_MINUTES:
            result["evaluations"][horizon_id] = {
                "status": "DATA_GAP",
                "target_time_utc": target.isoformat(),
                "first_available_price_time_utc": point.available_at_utc,
                "market_delay_minutes": round(market_delay_minutes, 2),
                "reason": "first complete traded price is too delayed; next open is never substituted for a fixed horizon",
            }
            continue

        actual_change = _pct_change(ref.close, point.close)
        post = _window(frame, decision_time, actual_point_time, include_start=False)
        post_range_pct = _range_pct(post, ref.close)
        baseline_range_pct = _baseline_range_pct(frame, decision_time, minutes, ref.close)
        directional_threshold = _direction_threshold_pct(baseline_range_pct)
        actual_direction = _actual_direction(actual_change, directional_threshold)
        mfe, mae = _mfe_mae(frame, ref_time, actual_point_time, ref.close, predicted_immediate)
        score = _score_non_directional(
            predicted_immediate,
            actual_change,
            post_range_pct,
            baseline_range_pct,
            directional_threshold,
        )

        result["evaluations"][horizon_id] = {
            "status": "DONE",
            "target_time_utc": target.isoformat(),
            "actual_price_time_utc": point.available_at_utc,
            "actual_price_bar_start_utc": point.bar_start_utc,
            "market_delay_minutes": round(market_delay_minutes, 2),
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

    statuses = [entry.get("status") for entry in result["evaluations"].values() if isinstance(entry, dict)]
    if statuses and all(status in TERMINAL_STATUSES for status in statuses):
        result["status"] = "DONE"
    elif any(status == "DONE" for status in statuses):
        result["status"] = "PARTIAL"
    else:
        result["status"] = "PENDING"
    return result


def _has_usable_context(context: dict) -> bool:
    regimes = context.get("regimes", {}) if isinstance(context, dict) else {}
    return any(value and value != "UNKNOWN" for value in regimes.values())


def evaluate_prediction(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        raw_prediction = json.load(f)

    prediction = normalize_prediction(raw_prediction)
    errors, warnings = validate_normalized_prediction(prediction, set(load_instruments()))
    if errors:
        raise ValueError(
            f"Prediction {prediction.get('prediction_id', path.name)} failed normalized schema: " + "; ".join(errors)
        )

    event_time_value = prediction.get("event_time_utc") or prediction.get("published_at_utc")
    event_time = _parse_utc(event_time_value)
    decision_time, created_at, latency = _decision_time(event_time, prediction.get("created_at_utc"))
    prediction_id = prediction["prediction_id"]

    stored_raw_context = raw_prediction.get("market_context_at_prediction")
    normalized_stored_context = normalize_market_context(stored_raw_context)
    if _has_usable_context(normalized_stored_context):
        market_context = normalized_stored_context
        context_origin = "captured_at_prediction_normalized"
    elif bool(prediction.get("eligible_for_hit_rate", True)) and not bool(prediction.get("backfilled", False)):
        market_context = fetch_pre_event_context(decision_time)
        context_origin = "reconstructed_pre_decision_from_yahoo"
    else:
        market_context = normalized_stored_context
        context_origin = "missing_or_unusable_context_ineligible_record"

    return {
        "evaluation_version": EVALUATION_VERSION,
        "evaluation_config_hash": _config_hash(),
        "prediction_id": prediction_id,
        "event_id": prediction.get("event_id"),
        "event_time_utc": event_time.isoformat(),
        "prediction_time_utc": None if created_at is None else created_at.isoformat(),
        "evaluation_anchor_time_utc": decision_time.isoformat(),
        "prediction_latency_seconds": None if latency is None else round(latency, 3),
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_version": prediction.get("model_version"),
        "prediction_model_version": prediction.get("prediction_model_version"),
        "methodology_version": prediction.get("methodology_version"),
        "categories": prediction.get("categories", []),
        "is_example": bool(prediction.get("is_example", False)),
        "backfilled": bool(prediction.get("backfilled", False)),
        "eligible_for_hit_rate": bool(prediction.get("eligible_for_hit_rate", True)) and not bool(prediction.get("is_example", False)),
        "normalization_warnings": warnings,
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

    out_dir = ROOT / EVAL_CONFIG.get("output", {}).get("evaluations_dir", "data/evaluations_v2")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{output['prediction_id']}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
