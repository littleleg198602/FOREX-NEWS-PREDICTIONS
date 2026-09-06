from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
import math

from src.config import ROOT, load_evaluation_config, load_yaml
from src.market_data.context_snapshot import context_signature
from src.prediction.normalization import normalize_prediction

HORIZONS = ("15m", "1h", "4h", "next_session")
PRIOR_ALPHA = 2.0
PRIOR_BETA = 2.0
EVAL_CONFIG = load_evaluation_config()


def _learning_config() -> dict:
    return load_yaml("config/market_context.yaml").get("learning", {})


def _thresholds() -> dict:
    cfg = _learning_config()
    return {
        "early": int(cfg.get("minimum_sample_early_signal", 10)),
        "actionable": int(cfg.get("minimum_sample_actionable", 30)),
        "strong": int(cfg.get("strong_sample", 75)),
        "unique_early": int(cfg.get("minimum_unique_events_early_signal", 5)),
        "unique_actionable": int(cfg.get("minimum_unique_events_actionable", 15)),
        "unique_strong": int(cfg.get("strong_unique_events", 30)),
        "good": float(cfg.get("actionable_min_hit_rate_pct", 58.0)),
        "bad": float(cfg.get("actionable_max_hit_rate_pct", 42.0)),
    }


def _confidence_bucket(value: int | float | None) -> str:
    if value is None:
        return "UNKNOWN"
    v = float(value)
    if v <= 4:
        return "1-4"
    if v <= 6:
        return "5-6"
    if v <= 8:
        return "7-8"
    return "9-10"


def _wilson_lower_bound(correct: float, n: int, z: float = 1.96) -> float | None:
    if n <= 0:
        return None
    phat = correct / n
    z2 = z * z
    denominator = 1.0 + z2 / n
    centre = phat + z2 / (2.0 * n)
    margin = z * math.sqrt((phat * (1.0 - phat) / n) + z2 / (4.0 * n * n))
    return (centre - margin) / denominator


def _new_counter() -> dict:
    return {
        "n": 0,
        "correct": 0,
        "sum_change_pct": 0.0,
        "event_ids": set(),
        "event_scores": defaultdict(lambda: {"n": 0, "correct": 0}),
    }


def _add(counter: dict, correct: bool, change_pct: float, event_id: str | None = None) -> None:
    counter["n"] += 1
    counter["correct"] += int(bool(correct))
    counter["sum_change_pct"] += change_pct
    if event_id is not None:
        event_key = str(event_id)
        counter.setdefault("event_ids", set()).add(event_key)
        event_scores = counter.setdefault("event_scores", defaultdict(lambda: {"n": 0, "correct": 0}))
        event_scores[event_key]["n"] += 1
        event_scores[event_key]["correct"] += int(bool(correct))


def _event_weighted_stats(counter: dict) -> tuple[int, float]:
    event_scores = counter.get("event_scores")
    if event_scores:
        means = []
        for stats in event_scores.values():
            if stats.get("n", 0) > 0:
                means.append(stats.get("correct", 0) / stats["n"])
        if means:
            return len(means), float(sum(means))

    ids = counter.get("event_ids")
    if ids:
        # Legacy/manual counter with IDs but without per-event outcomes. We know
        # independence count but cannot reconstruct exact event weighting.
        unique = len(ids)
        raw = 0.0 if counter.get("n", 0) <= 0 else counter.get("correct", 0) / counter["n"]
        return unique, raw * unique

    n = int(counter.get("n", 0))
    return n, float(counter.get("correct", 0))


def _finalize(counter: dict) -> dict:
    observation_n = int(counter.get("n", 0))
    observation_correct = int(counter.get("correct", 0))
    t = _thresholds()
    unique_events, weighted_successes = _event_weighted_stats(counter)

    if observation_n == 0:
        return {
            "n": 0,
            "unique_events": 0,
            "correct": 0,
            "raw_hit_rate_pct": None,
            "event_weighted_hit_rate_pct": None,
            "bayesian_hit_rate_pct": None,
            "wilson_lower_95_pct": None,
            "mean_change_pct": None,
            "sample_status": "INSUFFICIENT",
            "learning_weight": 0.0,
        }

    weighted_raw = None if unique_events <= 0 else weighted_successes / unique_events
    bayes = None if unique_events <= 0 else (weighted_successes + PRIOR_ALPHA) / (unique_events + PRIOR_ALPHA + PRIOR_BETA)
    wilson = None if unique_events <= 0 else _wilson_lower_bound(weighted_successes, unique_events)

    if observation_n >= t["actionable"] and unique_events >= t["unique_actionable"]:
        sample_status = "ACTIONABLE"
        learning_weight = min(
            1.0,
            observation_n / max(t["strong"], 1),
            unique_events / max(t["unique_strong"], 1),
        )
    elif observation_n >= t["early"] and unique_events >= t["unique_early"]:
        sample_status = "EARLY_SIGNAL"
        learning_weight = min(
            0.35,
            observation_n / max(t["strong"], 1),
            unique_events / max(t["unique_strong"], 1),
        )
    else:
        sample_status = "INSUFFICIENT"
        learning_weight = 0.0

    raw_observation_rate = observation_correct / observation_n
    return {
        "n": observation_n,
        "unique_events": unique_events,
        "correct": observation_correct,
        "raw_hit_rate_pct": round(raw_observation_rate * 100.0, 2),
        "event_weighted_hit_rate_pct": None if weighted_raw is None else round(weighted_raw * 100.0, 2),
        "bayesian_hit_rate_pct": None if bayes is None else round(bayes * 100.0, 2),
        "wilson_lower_95_pct": None if wilson is None else round(wilson * 100.0, 2),
        "mean_change_pct": round(counter.get("sum_change_pct", 0.0) / observation_n, 6),
        "sample_status": sample_status,
        "learning_weight": round(learning_weight, 3),
    }


def _recommendation(stats: dict) -> str:
    if stats["sample_status"] == "INSUFFICIENT":
        return "NO_CHANGE"
    if stats["sample_status"] == "EARLY_SIGNAL":
        return "WATCH_ONLY"
    if stats["sample_status"] != "ACTIONABLE":
        return "KEEP_NEUTRAL"

    t = _thresholds()
    rate = stats["bayesian_hit_rate_pct"]
    lower = stats["wilson_lower_95_pct"]
    if lower is not None and lower >= t["good"]:
        return "BOOST_CONFIDENCE"
    if rate is not None and rate <= t["bad"]:
        return "REDUCE_OR_AVOID"
    return "KEEP_NEUTRAL"


def main() -> int:
    predictions_root = ROOT / "data" / "predictions"
    evaluations_root = ROOT / EVAL_CONFIG.get("output", {}).get("evaluations_dir", "data/evaluations_v2")
    out_root = ROOT / EVAL_CONFIG.get("output", {}).get("statistics_dir", "data/statistics_v2")
    out_root.mkdir(parents=True, exist_ok=True)

    predictions: dict[str, dict] = {}
    for path in predictions_root.rglob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            normalized = normalize_prediction(raw)
            predictions[normalized["prediction_id"]] = normalized
        except Exception:
            continue

    by_instrument = defaultdict(_new_counter)
    by_category = defaultdict(_new_counter)
    by_confidence = defaultdict(_new_counter)
    by_score_type = defaultdict(_new_counter)
    by_instrument_category = defaultdict(_new_counter)
    by_context = defaultdict(_new_counter)
    by_context_signature = defaultdict(_new_counter)
    by_instrument_context = defaultdict(_new_counter)
    by_category_context = defaultdict(_new_counter)
    by_instrument_category_context = defaultdict(_new_counter)

    audit = {
        "evaluation_version": EVAL_CONFIG.get("evaluation_version"),
        "prediction_files": len(predictions),
        "evaluation_files": 0,
        "eligible_evaluation_files": 0,
        "excluded_ineligible": 0,
        "excluded_examples": 0,
        "scored_items": 0,
        "scored_items_with_context": 0,
        "scored_items_without_context": 0,
    }

    for path in evaluations_root.glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                evaluation = json.load(f)
        except Exception:
            continue

        if evaluation.get("evaluation_version") != EVAL_CONFIG.get("evaluation_version"):
            continue
        audit["evaluation_files"] += 1
        prediction_id = evaluation.get("prediction_id")
        prediction = predictions.get(prediction_id)
        if not prediction:
            continue

        if bool(prediction.get("is_example", False)) or bool(evaluation.get("is_example", False)):
            audit["excluded_examples"] += 1
            continue

        eligible = bool(evaluation.get("eligible_for_hit_rate", prediction.get("eligible_for_hit_rate", True)))
        if not eligible or bool(prediction.get("backfilled", False)):
            audit["excluded_ineligible"] += 1
            continue
        audit["eligible_evaluation_files"] += 1

        learning_event_id = str(prediction.get("event_id") or prediction_id)
        categories = prediction.get("categories") or ["UNKNOWN"]
        model_version = str(evaluation.get("model_version") or prediction.get("model_version") or "UNKNOWN")
        pred_by_instrument = {
            item.get("instrument"): item
            for item in prediction.get("predictions", [])
            if item.get("instrument")
        }
        market_context = evaluation.get("market_context") or prediction.get("market_context_at_prediction") or {}
        all_regimes = market_context.get("regimes", {})
        regimes = {name: regime for name, regime in all_regimes.items() if regime and regime != "UNKNOWN"}
        signature = context_signature(market_context) if regimes else "NO_CONTEXT"

        for result in evaluation.get("results", []):
            instrument = result.get("instrument")
            pred_item = pred_by_instrument.get(instrument, {})

            for horizon in HORIZONS:
                scored = result.get("evaluations", {}).get(horizon, {})
                if scored.get("status") != "DONE" or scored.get("correct") is None:
                    continue

                score_type = scored.get("score_type", "directional")
                confidence_source = pred_item.get("next_session", {}) if horizon == "next_session" else pred_item.get("immediate", {})
                confidence_bucket = _confidence_bucket(confidence_source.get("confidence"))
                correct = bool(scored["correct"])
                change_pct = float(scored.get("change_pct", 0.0))
                audit["scored_items"] += 1

                # Every learning key includes model_version + score_type. A
                # successful MIXED/VOLATILITY item can therefore never change a
                # directional segment, and model versions are never pooled.
                _add(by_instrument[(model_version, score_type, instrument, horizon)], correct, change_pct, learning_event_id)
                _add(by_confidence[(model_version, score_type, confidence_bucket, horizon)], correct, change_pct, learning_event_id)
                _add(by_score_type[(model_version, score_type, horizon)], correct, change_pct, learning_event_id)

                for category in categories:
                    _add(by_category[(model_version, score_type, category, horizon)], correct, change_pct, learning_event_id)
                    _add(by_instrument_category[(model_version, score_type, instrument, category, horizon)], correct, change_pct, learning_event_id)

                if regimes:
                    audit["scored_items_with_context"] += 1
                    _add(by_context_signature[(model_version, score_type, signature, horizon)], correct, change_pct, learning_event_id)
                    for context_name, regime in regimes.items():
                        _add(by_context[(model_version, score_type, context_name, regime, horizon)], correct, change_pct, learning_event_id)
                        _add(by_instrument_context[(model_version, score_type, instrument, context_name, regime, horizon)], correct, change_pct, learning_event_id)
                        for category in categories:
                            _add(by_category_context[(model_version, score_type, category, context_name, regime, horizon)], correct, change_pct, learning_event_id)
                            _add(
                                by_instrument_category_context[(model_version, score_type, instrument, category, context_name, regime, horizon)],
                                correct,
                                change_pct,
                                learning_event_id,
                            )
                else:
                    audit["scored_items_without_context"] += 1

    omitted: dict[str, int] = {}

    def pack(name: str, mapping: dict, key_names: tuple[str, ...]) -> list[dict]:
        rows = []
        omitted_count = 0
        for key, counter in sorted(mapping.items(), key=lambda x: tuple(str(v) for v in x[0])):
            values = key if isinstance(key, tuple) else (key,)
            stats = _finalize(counter)
            if stats["sample_status"] == "INSUFFICIENT":
                omitted_count += 1
                continue
            row = {key_name: value for key_name, value in zip(key_names, values)}
            row.update(stats)
            row["recommendation"] = _recommendation(stats)
            rows.append(row)
        omitted[name] = omitted_count
        return rows

    t = _thresholds()
    profile = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "profile_version": "2.0.0",
        "evaluation_version": EVAL_CONFIG.get("evaluation_version"),
        "purpose": "Evidence-based priors for future Forex Factory predictions from leakage-safe evaluation v2. Never rewrite historical predictions.",
        "guardrails": {
            "minimum_sample_actionable": t["actionable"],
            "minimum_sample_early_signal": t["early"],
            "strong_sample": t["strong"],
            "minimum_unique_events_early_signal": t["unique_early"],
            "minimum_unique_events_actionable": t["unique_actionable"],
            "strong_unique_events": t["unique_strong"],
            "actionable_min_hit_rate_pct": t["good"],
            "actionable_max_hit_rate_pct": t["bad"],
            "bayesian_prior": {"alpha": PRIOR_ALPHA, "beta": PRIOR_BETA},
            "event_independence_unit": "event_id; prediction_id only as fallback",
            "event_weighting": "Each event contributes total weight 1 inside a segment, split across correlated instrument observations.",
            "score_type_isolation": "directional, mixed_neutral and volatility are never pooled for learning recommendations",
            "model_version_isolation": "different prediction model versions are never pooled in learning segments",
            "rule": "Only ACTIONABLE segments may materially change future confidence. EARLY_SIGNAL is advisory only; INSUFFICIENT causes no change.",
            "anti_leakage": "Market context and price anchors use only bars whose close was available at or before prediction decision time.",
        },
        "audit": audit,
        "omitted_insufficient_segments": omitted,
        "confidence_calibration": pack("confidence_calibration", by_confidence, ("model_version", "score_type", "confidence_bucket", "horizon")),
        "by_instrument": pack("by_instrument", by_instrument, ("model_version", "score_type", "instrument", "horizon")),
        "by_category": pack("by_category", by_category, ("model_version", "score_type", "category", "horizon")),
        "by_score_type": pack("by_score_type", by_score_type, ("model_version", "score_type", "horizon")),
        "by_instrument_category": pack("by_instrument_category", by_instrument_category, ("model_version", "score_type", "instrument", "category", "horizon")),
        "by_context": pack("by_context", by_context, ("model_version", "score_type", "context", "regime", "horizon")),
        "by_context_signature": pack("by_context_signature", by_context_signature, ("model_version", "score_type", "context_signature", "horizon")),
        "by_instrument_context": pack("by_instrument_context", by_instrument_context, ("model_version", "score_type", "instrument", "context", "regime", "horizon")),
        "by_category_context": pack("by_category_context", by_category_context, ("model_version", "score_type", "category", "context", "regime", "horizon")),
        "by_instrument_category_context": pack(
            "by_instrument_category_context",
            by_instrument_category_context,
            ("model_version", "score_type", "instrument", "category", "context", "regime", "horizon"),
        ),
    }
    profile["omitted_insufficient_segments"] = dict(omitted)

    out_path = out_root / "learning_profile.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
