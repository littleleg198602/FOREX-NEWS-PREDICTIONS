from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

ALLOWED_DIRECTIONS = {"UP", "DOWN", "MIXED", "VOLATILITY"}
CONTEXT_FACTORS = ("DXY", "US2Y", "US10Y", "VIX", "WTI", "BRENT")


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _parse_utc_optional(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _canonical_factor_name(name: str) -> str | None:
    normalized = str(name).strip().upper().replace("_", "")
    aliases = {
        "DXY": "DXY",
        "USDINDEX": "DXY",
        "US2Y": "US2Y",
        "2Y": "US2Y",
        "US10Y": "US10Y",
        "10Y": "US10Y",
        "VIX": "VIX",
        "WTI": "WTI",
        "CL": "WTI",
        "BRENT": "BRENT",
        "BZ": "BRENT",
    }
    return aliases.get(normalized)


def _canonical_regime(factor: str, item: dict, explicit: Any = None) -> str:
    value = item.get("value")
    if factor == "VIX":
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = None
        if numeric is not None:
            if numeric >= 25.0:
                return "HIGH"
            if numeric < 18.0:
                return "LOW"
            return "ELEVATED"

    text_parts = [
        str(item.get("short_term_direction") or ""),
        str(item.get("direction") or ""),
        str(explicit or ""),
        str(item.get("regime") or ""),
    ]
    text = " ".join(text_parts).upper().replace("-", "_")

    if factor == "VIX":
        if "HIGH" in text or "PANIC" in text or "RISK_OFF" in text:
            return "HIGH"
        if "LOW" in text or "COMPLAC" in text:
            return "LOW"
        if "ELEV" in text:
            return "ELEVATED"
        return "UNKNOWN"

    # A description like UP_THEN_FADED or UP_THEN_STALLED is not a clean
    # directional trend at decision time. Keep it neutral instead of forcing UP.
    if "FADE" in text or "STALL" in text or "MIXED" in text or "FLAT" in text or "STABLE" in text:
        return "FLAT"
    if any(token in text for token in ("FALL", "DOWN", "LOWER", "WEAK", "EASING", "DOVISH")):
        return "FALLING"
    if any(token in text for token in ("RISING", "RISE", " UP", "UP_", "HIGHER", "FIRM", "STRENGTH", "HAWK", "TIGHTEN")):
        return "RISING"
    if text.strip() in {"UP", "RISING"}:
        return "RISING"
    if text.strip() in {"DOWN", "FALLING"}:
        return "FALLING"
    return "UNKNOWN"


def normalize_market_context(raw_context: Any) -> dict:
    raw = _as_dict(raw_context)
    direct_regimes = _as_dict(raw.get("regimes"))
    direct_series = _as_dict(raw.get("series"))

    series: dict[str, dict] = {}
    regimes: dict[str, str] = {}
    adapted = False

    # Canonical series format, if already present.
    for raw_name, raw_item in direct_series.items():
        factor = _canonical_factor_name(raw_name)
        if factor is None or not isinstance(raw_item, dict):
            continue
        item = deepcopy(raw_item)
        explicit = direct_regimes.get(raw_name) or direct_regimes.get(factor)
        item["regime"] = _canonical_regime(factor, item, explicit)
        series[factor] = item
        regimes[factor] = item["regime"]

    # Historical/live external automation often stored DXY/US2Y/etc directly
    # at the context root. Adapt those records without mutating the prediction.
    for raw_name, raw_item in raw.items():
        factor = _canonical_factor_name(raw_name)
        if factor is None or not isinstance(raw_item, dict):
            continue
        if factor in series:
            continue
        adapted = True
        item = deepcopy(raw_item)
        timestamp = (
            item.get("timestamp_utc")
            or item.get("value_timestamp_utc")
            or item.get("captured_at_utc")
            or item.get("context_timestamp_utc")
        )
        if timestamp is not None:
            item["timestamp_utc"] = timestamp
        explicit = direct_regimes.get(raw_name) or direct_regimes.get(factor)
        item["regime"] = _canonical_regime(factor, item, explicit)
        series[factor] = item
        regimes[factor] = item["regime"]

    # Regime-only contexts are still useful; preserve them as UNKNOWN-value
    # canonical series entries.
    for raw_name, raw_regime in direct_regimes.items():
        factor = _canonical_factor_name(raw_name)
        if factor is None:
            continue
        if factor not in series:
            adapted = adapted or raw_name != factor
            item = {"value": None, "regime": _canonical_regime(factor, {}, raw_regime)}
            series[factor] = item
            regimes[factor] = item["regime"]

    # Make missing context explicit instead of silently dropping it.
    for factor in CONTEXT_FACTORS:
        if factor not in series:
            series[factor] = {
                "value": None,
                "timestamp_utc": None,
                "regime": "UNKNOWN",
                "source": None,
            }
            regimes[factor] = "UNKNOWN"

    captured_for = (
        raw.get("captured_for_time_utc")
        or raw.get("captured_for_event_time_utc")
        or raw.get("context_timestamp_utc")
        or raw.get("captured_at_utc")
    )

    return {
        "captured_for_time_utc": captured_for,
        "information_cutoff": raw.get("information_cutoff"),
        "source": raw.get("source"),
        "series": series,
        "regimes": regimes,
        "normalization": {
            "schema": "market_context_v2",
            "adapted_from_legacy_shape": adapted or not bool(direct_series),
        },
    }


def normalize_prediction(raw_prediction: dict) -> dict:
    raw = deepcopy(raw_prediction)
    source = _as_dict(raw.get("source"))
    eligibility = _as_dict(raw.get("eligibility"))
    warnings: list[str] = []

    prediction_id = raw.get("prediction_id")
    if not prediction_id and raw.get("id"):
        prediction_id = raw.get("id")
        warnings.append("prediction_id adapted from id")

    published_at = raw.get("published_at_utc") or source.get("published_at_utc")
    event_time = raw.get("event_time_utc") or source.get("event_time_utc") or published_at
    if raw.get("published_at_utc") is None and source.get("published_at_utc"):
        warnings.append("published_at_utc adapted from source.published_at_utc")

    eligible = raw.get("eligible_for_hit_rate")
    if eligible is None and "eligible_for_hit_rate" in eligibility:
        eligible = eligibility.get("eligible_for_hit_rate")
        warnings.append("eligible_for_hit_rate adapted from eligibility")
    if eligible is None:
        eligible = True

    backfilled = raw.get("backfilled")
    if backfilled is None and "backfilled" in eligibility:
        backfilled = eligibility.get("backfilled")
        warnings.append("backfilled adapted from eligibility")
    backfilled = bool(backfilled)

    categories = raw.get("categories")
    if not categories and raw.get("category"):
        categories = [raw.get("category")]
        warnings.append("categories adapted from singular category")
    categories = [str(value) for value in _as_list(categories) if value not in (None, "")]
    if not categories:
        categories = ["UNKNOWN"]

    top_level_next = {
        item.get("instrument"): item
        for item in _as_list(raw.get("next_session"))
        if isinstance(item, dict) and item.get("instrument")
    }

    normalized_predictions: list[dict] = []
    for item in _as_list(raw.get("predictions")):
        if not isinstance(item, dict):
            continue
        out = deepcopy(item)
        instrument = out.get("instrument")
        if not isinstance(out.get("immediate"), dict):
            direction = out.get("direction")
            confidence = out.get("confidence")
            if direction is not None or confidence is not None:
                out["immediate"] = {
                    "direction": direction,
                    "confidence": confidence,
                }
                warnings.append(f"{instrument or 'UNKNOWN'} immediate adapted from flat direction/confidence")
        if not isinstance(out.get("next_session"), dict) and instrument in top_level_next:
            legacy_next = top_level_next[instrument]
            out["next_session"] = {
                "direction": legacy_next.get("direction"),
                "confidence": legacy_next.get("confidence"),
            }
            warnings.append(f"{instrument} next_session adapted from top-level array")
        if "mechanism" not in out and raw.get("mechanism"):
            out["mechanism"] = raw.get("mechanism")
        if "invalidation" not in out and raw.get("invalidation"):
            out["invalidation"] = raw.get("invalidation")
        normalized_predictions.append(out)

    normalized = deepcopy(raw)
    normalized.update(
        {
            "prediction_id": prediction_id,
            "event_id": raw.get("event_id"),
            "created_at_utc": raw.get("created_at_utc"),
            "published_at_utc": published_at,
            "event_time_utc": event_time,
            "model_version": raw.get("model_version") or raw.get("prediction_model_version"),
            "prediction_model_version": raw.get("prediction_model_version") or raw.get("model_version"),
            "methodology_version": raw.get("methodology_version"),
            "categories": categories,
            "eligible_for_hit_rate": bool(eligible),
            "backfilled": backfilled,
            "predictions": normalized_predictions,
            "market_context_at_prediction": normalize_market_context(raw.get("market_context_at_prediction")),
            "normalization": {
                "schema": "prediction_v2_normalized",
                "warnings": warnings,
            },
        }
    )
    return normalized


def validate_normalized_prediction(prediction: dict, known_instruments: set[str] | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = list(_as_dict(prediction.get("normalization")).get("warnings", []))

    if not prediction.get("prediction_id"):
        errors.append("missing prediction_id")
    if not prediction.get("event_time_utc") and not prediction.get("published_at_utc"):
        errors.append("missing event_time_utc/published_at_utc")
    if prediction.get("eligible_for_hit_rate", True) and not prediction.get("created_at_utc"):
        errors.append("eligible live prediction missing created_at_utc")

    prediction_items = prediction.get("predictions")
    if not isinstance(prediction_items, list) or not prediction_items:
        errors.append("predictions must be a non-empty list")
        return errors, warnings

    for index, item in enumerate(prediction_items):
        if not isinstance(item, dict):
            errors.append(f"predictions[{index}] is not an object")
            continue
        instrument = item.get("instrument")
        if not instrument:
            errors.append(f"predictions[{index}] missing instrument")
        elif known_instruments is not None and instrument not in known_instruments:
            errors.append(f"predictions[{index}] unknown instrument {instrument}")

        immediate = item.get("immediate")
        if not isinstance(immediate, dict):
            errors.append(f"predictions[{index}] missing immediate object")
            continue
        direction = str(immediate.get("direction") or "").upper()
        if direction not in ALLOWED_DIRECTIONS:
            errors.append(f"predictions[{index}] invalid immediate direction {direction!r}")
        confidence = immediate.get("confidence")
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            confidence_value = None
        if confidence_value is None or not 1 <= confidence_value <= 10:
            errors.append(f"predictions[{index}] immediate confidence must be 1..10")

        next_session = item.get("next_session")
        if next_session is not None:
            if not isinstance(next_session, dict):
                errors.append(f"predictions[{index}] next_session must be an object")
            else:
                next_direction = str(next_session.get("direction") or "").upper()
                if next_direction and next_direction not in ALLOWED_DIRECTIONS:
                    errors.append(f"predictions[{index}] invalid next_session direction {next_direction!r}")
                if next_direction:
                    try:
                        next_confidence = float(next_session.get("confidence"))
                    except (TypeError, ValueError):
                        next_confidence = None
                    if next_confidence is None or not 1 <= next_confidence <= 10:
                        errors.append(f"predictions[{index}] next_session confidence must be 1..10")

    for field in ("created_at_utc", "event_time_utc", "published_at_utc"):
        value = prediction.get(field)
        if value and _parse_utc_optional(value) is None:
            errors.append(f"invalid UTC timestamp in {field}")

    return errors, warnings
