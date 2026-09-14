from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

from src.config import ROOT, load_instruments
from src.evaluation import evaluate_prediction as legacy
from src.market_data.context_snapshot import fetch_pre_event_context
from src.market_data.yahoo_provider import fetch_1m_window, first_complete_bar_at_or_after, last_complete_bar_before
from src.prediction.forecast import forecast_for_horizon, has_explicit_horizon_forecasts
from src.prediction.normalization import normalize_market_context, normalize_prediction, validate_normalized_prediction


def evaluate_one_instrument(prediction_id: str, decision_time: datetime, item: dict) -> dict:
    instrument = item["instrument"]
    now = datetime.now(timezone.utc)
    instrument_cfg = load_instruments().get(instrument, {})
    fifteen = forecast_for_horizon(item, "15m")

    try:
        frame = fetch_1m_window(
            instrument,
            decision_time,
            before_minutes=legacy.MAX_MARKET_WINDOW_MINUTES,
            after_minutes=legacy._forward_minutes(decision_time, now),
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
                horizon: {"status": "NO_REFERENCE_PRICE"} for horizon in legacy.FIXED_HORIZONS
            } | {"next_session": {"status": "NO_REFERENCE_PRICE"}},
        }

    ref_time = legacy._parse_utc(ref.available_at_utc)
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
        "forecast_structure": "explicit_horizons" if has_explicit_horizon_forecasts(item) else "legacy_immediate_fallback",
        "predicted_immediate_direction": str(fifteen.get("direction") or "").upper() or None,
        "predicted_confidence": fifteen.get("confidence"),
        "evaluations": {},
    }

    for horizon_id, minutes in legacy.FIXED_HORIZONS.items():
        forecast = forecast_for_horizon(item, horizon_id)
        predicted = str(forecast.get("direction") or "").upper()
        confidence = forecast.get("confidence")
        if not predicted:
            result["evaluations"][horizon_id] = {"status": "NOT_PREDICTED"}
            continue

        target = decision_time + timedelta(minutes=minutes)
        if now < target:
            result["evaluations"][horizon_id] = {
                "status": "PENDING",
                "target_time_utc": target.isoformat(),
                "predicted_direction": predicted,
                "predicted_confidence": confidence,
            }
            continue

        if reference_age_minutes > legacy.REFERENCE_MAX_AGE_MINUTES:
            result["evaluations"][horizon_id] = {
                "status": "MARKET_CLOSED",
                "target_time_utc": target.isoformat(),
                "predicted_direction": predicted,
                "predicted_confidence": confidence,
                "reason": "reference price was stale at decision time; fixed clock-time reaction is not scoreable",
                "reference_age_minutes": round(reference_age_minutes, 3),
            }
            continue

        point = first_complete_bar_at_or_after(frame, target)
        if point is None:
            result["evaluations"][horizon_id] = {
                "status": "DATA_GAP",
                "target_time_utc": target.isoformat(),
                "predicted_direction": predicted,
                "predicted_confidence": confidence,
                "reason": "no complete traded bar available at/after target",
            }
            continue

        actual_point_time = legacy._parse_utc(point.available_at_utc)
        market_delay_minutes = max(0.0, (actual_point_time - target).total_seconds() / 60.0)
        if market_delay_minutes > legacy.MAX_MARKET_DELAY_MINUTES:
            result["evaluations"][horizon_id] = {
                "status": "DATA_GAP",
                "target_time_utc": target.isoformat(),
                "predicted_direction": predicted,
                "predicted_confidence": confidence,
                "first_available_price_time_utc": point.available_at_utc,
                "market_delay_minutes": round(market_delay_minutes, 2),
                "reason": "first complete traded price is too delayed; next open is never substituted for a fixed horizon",
            }
            continue

        actual_change = legacy._pct_change(ref.close, point.close)
        post = legacy._window(frame, decision_time, actual_point_time, include_start=False)
        post_range_pct = legacy._range_pct(post, ref.close)
        baseline_range_pct = legacy._baseline_range_pct(frame, decision_time, minutes, ref.close)
        directional_threshold = legacy._direction_threshold_pct(baseline_range_pct)
        actual_direction = legacy._actual_direction(actual_change, directional_threshold)
        mfe, mae = legacy._mfe_mae(frame, ref_time, actual_point_time, ref.close, predicted)
        score = legacy._score_non_directional(
            predicted,
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
            "predicted_direction": predicted,
            "predicted_confidence": confidence,
            "forecast_source": "horizons" if isinstance(item.get("horizons", {}).get(horizon_id), dict) else "legacy_fallback",
            "correct": score.get("correct"),
            "score_type": score.get("score_type"),
            "baseline_range_pct": None if baseline_range_pct is None else round(baseline_range_pct, 6),
            "post_event_range_pct": None if post_range_pct is None else round(post_range_pct, 6),
            "mfe_pct": None if mfe is None else round(mfe, 6),
            "mae_pct": None if mae is None else round(mae, 6),
            **{k: v for k, v in score.items() if k not in {"correct", "score_type"}},
        }

    session_forecast = forecast_for_horizon(item, "next_session")
    session_item = deepcopy(item)
    if session_forecast:
        session_item["next_session"] = session_forecast
    session_eval = legacy._evaluate_next_session(
        frame,
        instrument,
        decision_time,
        ref_time,
        ref.close,
        session_item,
        now,
    )
    if isinstance(session_eval, dict) and session_forecast:
        session_eval["forecast_source"] = (
            "horizons" if isinstance(item.get("horizons", {}).get("next_session"), dict) else "legacy_fallback"
        )
    result["evaluations"]["next_session"] = session_eval

    statuses = [entry.get("status") for entry in result["evaluations"].values() if isinstance(entry, dict)]
    if statuses and all(status in legacy.TERMINAL_STATUSES for status in statuses):
        result["status"] = "DONE"
    elif any(status == "DONE" for status in statuses):
        result["status"] = "PARTIAL"
    else:
        result["status"] = "PENDING"
    return result


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
    event_time = legacy._parse_utc(event_time_value)
    decision_time, created_at, latency = legacy._decision_time(event_time, prediction.get("created_at_utc"))
    prediction_id = prediction["prediction_id"]

    stored_raw_context = raw_prediction.get("market_context_at_prediction")
    normalized_stored_context = normalize_market_context(stored_raw_context)
    if legacy._has_usable_context(normalized_stored_context):
        market_context = normalized_stored_context
        context_origin = "captured_at_prediction_normalized"
    elif bool(prediction.get("eligible_for_hit_rate", True)) and not bool(prediction.get("backfilled", False)):
        market_context = fetch_pre_event_context(decision_time)
        context_origin = "reconstructed_pre_decision_from_yahoo"
    else:
        market_context = normalized_stored_context
        context_origin = "missing_or_unusable_context_ineligible_record"

    return {
        "evaluation_version": legacy.EVALUATION_VERSION,
        "evaluation_config_hash": legacy._config_hash(),
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
        "evidence": prediction.get("evidence"),
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
        print("Usage: python -m src.evaluation.evaluate_prediction_model2 data/predictions/example.json")
        return 2
    src_path = Path(sys.argv[1])
    output = evaluate_prediction(src_path)
    out_dir = ROOT / legacy.EVAL_CONFIG.get("output", {}).get("evaluations_dir", "data/evaluations_v2")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{output['prediction_id']}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
