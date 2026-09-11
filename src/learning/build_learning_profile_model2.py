from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json

from src.config import ROOT, load_evaluation_config
from src.learning import build_learning_profile as legacy
from src.market_data.context_snapshot import context_signature
from src.prediction.forecast import forecast_for_horizon
from src.prediction.normalization import normalize_prediction
from src.prediction.taxonomy import canonical_categories, canonical_label

HORIZONS = ("15m", "1h", "4h", "next_session")
EVAL_CONFIG = load_evaluation_config()


def _news_age_bucket(value) -> str:
    try:
        age = float(value)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if age < 5:
        return "0-5m"
    if age < 15:
        return "5-15m"
    if age < 30:
        return "15-30m"
    if age < 60:
        return "30-60m"
    if age < 120:
        return "60-120m"
    return "120m+"


def main() -> int:
    predictions_root = ROOT / "data" / "predictions"
    evaluations_root = ROOT / EVAL_CONFIG.get("output", {}).get("evaluations_dir", "data/evaluations_v2")
    out_root = ROOT / EVAL_CONFIG.get("output", {}).get("statistics_dir", "data/statistics_v2")
    out_root.mkdir(parents=True, exist_ok=True)

    predictions: dict[str, dict] = {}
    for path in predictions_root.rglob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            normalized = normalize_prediction(raw)
            predictions[normalized["prediction_id"]] = normalized
        except Exception:
            continue

    dimensions = {
        "by_instrument": defaultdict(legacy._new_counter),
        "by_category": defaultdict(legacy._new_counter),
        "by_confidence": defaultdict(legacy._new_counter),
        "by_score_type": defaultdict(legacy._new_counter),
        "by_instrument_category": defaultdict(legacy._new_counter),
        "by_context": defaultdict(legacy._new_counter),
        "by_context_signature": defaultdict(legacy._new_counter),
        "by_instrument_context": defaultdict(legacy._new_counter),
        "by_category_context": defaultdict(legacy._new_counter),
        "by_instrument_category_context": defaultdict(legacy._new_counter),
        "by_article_role": defaultdict(legacy._new_counter),
        "by_absorption_state": defaultdict(legacy._new_counter),
        "by_cross_asset_confirmation": defaultdict(legacy._new_counter),
        "by_novelty": defaultdict(legacy._new_counter),
        "by_news_age": defaultdict(legacy._new_counter),
        "by_relevance": defaultdict(legacy._new_counter),
        "by_evidence_combo": defaultdict(legacy._new_counter),
    }

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
        "scored_model2_items_with_evidence": 0,
        "scored_model2_items_without_evidence": 0,
        "event_cluster_id_used": 0,
    }

    for path in evaluations_root.glob("*.json"):
        try:
            evaluation = json.loads(path.read_text(encoding="utf-8"))
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

        event_cluster = prediction.get("event_cluster_id")
        if event_cluster:
            audit["event_cluster_id_used"] += 1
        learning_event_id = str(event_cluster or prediction.get("event_id") or prediction_id)
        categories = canonical_categories(prediction.get("categories") or ["UNKNOWN"])
        model_version = str(evaluation.get("model_version") or prediction.get("model_version") or "UNKNOWN")
        pred_by_instrument = {
            item.get("instrument"): item
            for item in prediction.get("predictions", [])
            if isinstance(item, dict) and item.get("instrument")
        }
        market_context = evaluation.get("market_context") or prediction.get("market_context_at_prediction") or {}
        all_regimes = market_context.get("regimes", {}) if isinstance(market_context, dict) else {}
        regimes = {
            canonical_label(name): canonical_label(regime)
            for name, regime in all_regimes.items()
            if regime and regime != "UNKNOWN"
        }
        signature = context_signature(market_context) if regimes else "NO_CONTEXT"

        evidence = prediction.get("evidence") if isinstance(prediction.get("evidence"), dict) else {}
        article_role = canonical_label(evidence.get("article_role"))
        absorption = evidence.get("absorption") if isinstance(evidence.get("absorption"), dict) else {}
        absorption_state = canonical_label(absorption.get("state"))
        cross = evidence.get("cross_asset_confirmation") if isinstance(evidence.get("cross_asset_confirmation"), dict) else {}
        cross_verdict = canonical_label(cross.get("verdict"))
        novelty = canonical_label(evidence.get("novelty"))
        news_age = _news_age_bucket(evidence.get("news_age_minutes"))
        evidence_combo = f"{article_role}|{absorption_state}|{cross_verdict}"

        for result in evaluation.get("results", []):
            instrument = result.get("instrument")
            pred_item = pred_by_instrument.get(instrument, {})
            relevance = canonical_label(pred_item.get("relevance"))
            for horizon in HORIZONS:
                scored = result.get("evaluations", {}).get(horizon, {})
                if scored.get("status") != "DONE" or scored.get("correct") is None:
                    continue
                score_type = scored.get("score_type", "directional")
                forecast = forecast_for_horizon(pred_item, horizon)
                confidence_bucket = legacy._confidence_bucket(forecast.get("confidence"))
                correct = bool(scored["correct"])
                change_pct = float(scored.get("change_pct", 0.0))
                audit["scored_items"] += 1

                def add(name: str, key) -> None:
                    legacy._add(dimensions[name][key], correct, change_pct, learning_event_id)

                add("by_instrument", (model_version, score_type, instrument, horizon))
                add("by_confidence", (model_version, score_type, confidence_bucket, horizon))
                add("by_score_type", (model_version, score_type, horizon))
                for category in categories:
                    add("by_category", (model_version, score_type, category, horizon))
                    add("by_instrument_category", (model_version, score_type, instrument, category, horizon))

                if regimes:
                    audit["scored_items_with_context"] += 1
                    add("by_context_signature", (model_version, score_type, signature, horizon))
                    for context_name, regime in regimes.items():
                        add("by_context", (model_version, score_type, context_name, regime, horizon))
                        add("by_instrument_context", (model_version, score_type, instrument, context_name, regime, horizon))
                        for category in categories:
                            add("by_category_context", (model_version, score_type, category, context_name, regime, horizon))
                            add("by_instrument_category_context", (model_version, score_type, instrument, category, context_name, regime, horizon))
                else:
                    audit["scored_items_without_context"] += 1

                if model_version == "2.0.0":
                    if evidence:
                        audit["scored_model2_items_with_evidence"] += 1
                    else:
                        audit["scored_model2_items_without_evidence"] += 1
                    add("by_article_role", (model_version, score_type, article_role, horizon))
                    add("by_absorption_state", (model_version, score_type, absorption_state, horizon))
                    add("by_cross_asset_confirmation", (model_version, score_type, cross_verdict, horizon))
                    add("by_novelty", (model_version, score_type, novelty, horizon))
                    add("by_news_age", (model_version, score_type, news_age, horizon))
                    add("by_relevance", (model_version, score_type, relevance, horizon))
                    add("by_evidence_combo", (model_version, score_type, evidence_combo, horizon))

    omitted: dict[str, int] = {}

    def pack(name: str, key_names: tuple[str, ...]) -> list[dict]:
        rows = []
        omitted_count = 0
        mapping = dimensions[name]
        for key, counter in sorted(mapping.items(), key=lambda x: tuple(str(v) for v in x[0])):
            stats = legacy._finalize(counter)
            if stats["sample_status"] == "INSUFFICIENT":
                omitted_count += 1
                continue
            row = {key_name: value for key_name, value in zip(key_names, key)}
            row.update(stats)
            row["recommendation"] = legacy._recommendation(stats)
            rows.append(row)
        omitted[name] = omitted_count
        return rows

    t = legacy._thresholds()
    profile = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "profile_version": "3.0.0",
        "evaluation_version": EVAL_CONFIG.get("evaluation_version"),
        "purpose": "Evidence-based priors for future predictions. Model 2 learns information-pattern quality, not only instrument/category coefficients. Historical predictions are immutable.",
        "guardrails": {
            "minimum_sample_actionable": t["actionable"],
            "minimum_sample_early_signal": t["early"],
            "strong_sample": t["strong"],
            "minimum_unique_events_early_signal": t["unique_early"],
            "minimum_unique_events_actionable": t["unique_actionable"],
            "strong_unique_events": t["unique_strong"],
            "actionable_min_hit_rate_pct": t["good"],
            "actionable_max_hit_rate_pct": t["bad"],
            "bayesian_prior": {"alpha": legacy.PRIOR_ALPHA, "beta": legacy.PRIOR_BETA},
            "event_independence_unit": "event_cluster_id when supplied; otherwise event_id; prediction_id only as final fallback",
            "event_weighting": "Each independent event/cluster contributes total weight 1 inside a segment, split across correlated instrument observations.",
            "taxonomy_normalization": "Derived learning labels are canonicalized for case/punctuation so GEOPOLITICS and geopolitics do not fragment evidence.",
            "score_type_isolation": "directional, mixed_neutral and volatility are never pooled",
            "model_version_isolation": "prediction model versions are never pooled",
            "horizon_isolation": "15m, 1h, 4h and next_session use the confidence and direction explicitly forecast for that horizon when available",
            "evidence_learning": "model 2 additionally learns article role, absorption, cross-asset confirmation, novelty, news age, instrument relevance and their combinations",
            "rule": "Only ACTIONABLE segments may materially change future confidence. EARLY_SIGNAL is advisory only; INSUFFICIENT causes no change.",
        },
        "audit": audit,
        "confidence_calibration": pack("by_confidence", ("model_version", "score_type", "confidence_bucket", "horizon")),
        "by_instrument": pack("by_instrument", ("model_version", "score_type", "instrument", "horizon")),
        "by_category": pack("by_category", ("model_version", "score_type", "category", "horizon")),
        "by_score_type": pack("by_score_type", ("model_version", "score_type", "horizon")),
        "by_instrument_category": pack("by_instrument_category", ("model_version", "score_type", "instrument", "category", "horizon")),
        "by_context": pack("by_context", ("model_version", "score_type", "context", "regime", "horizon")),
        "by_context_signature": pack("by_context_signature", ("model_version", "score_type", "context_signature", "horizon")),
        "by_instrument_context": pack("by_instrument_context", ("model_version", "score_type", "instrument", "context", "regime", "horizon")),
        "by_category_context": pack("by_category_context", ("model_version", "score_type", "category", "context", "regime", "horizon")),
        "by_instrument_category_context": pack("by_instrument_category_context", ("model_version", "score_type", "instrument", "category", "context", "regime", "horizon")),
        "by_article_role": pack("by_article_role", ("model_version", "score_type", "article_role", "horizon")),
        "by_absorption_state": pack("by_absorption_state", ("model_version", "score_type", "absorption_state", "horizon")),
        "by_cross_asset_confirmation": pack("by_cross_asset_confirmation", ("model_version", "score_type", "cross_asset_confirmation", "horizon")),
        "by_novelty": pack("by_novelty", ("model_version", "score_type", "novelty", "horizon")),
        "by_news_age": pack("by_news_age", ("model_version", "score_type", "news_age_bucket", "horizon")),
        "by_relevance": pack("by_relevance", ("model_version", "score_type", "relevance", "horizon")),
        "by_evidence_combo": pack("by_evidence_combo", ("model_version", "score_type", "evidence_combo", "horizon")),
    }
    profile["omitted_insufficient_segments"] = dict(omitted)

    out_path = out_root / "learning_profile.json"
    out_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
