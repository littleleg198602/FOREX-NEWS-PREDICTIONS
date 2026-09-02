from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
import math

from src.config import ROOT, load_yaml
from src.market_data.context_snapshot import context_signature

HORIZONS = ("15m", "1h", "4h", "next_session")
PRIOR_ALPHA = 2.0
PRIOR_BETA = 2.0


def _learning_config() -> dict:
    return load_yaml("config/market_context.yaml").get("learning", {})


def _thresholds() -> tuple[int, int, int, float, float]:
    cfg = _learning_config()
    early = int(cfg.get("minimum_sample_early_signal", 10))
    actionable = int(cfg.get("minimum_sample_actionable", 30))
    strong = int(cfg.get("strong_sample", 75))
    good = float(cfg.get("actionable_min_hit_rate_pct", 58.0))
    bad = float(cfg.get("actionable_max_hit_rate_pct", 42.0))
    return early, actionable, strong, good, bad


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


def _wilson_lower_bound(correct: int, n: int, z: float = 1.96) -> float | None:
    if n <= 0:
        return None
    phat = correct / n
    z2 = z * z
    denominator = 1.0 + z2 / n
    centre = phat + z2 / (2.0 * n)
    margin = z * math.sqrt((phat * (1.0 - phat) / n) + z2 / (4.0 * n * n))
    return (centre - margin) / denominator


def _new_counter() -> dict:
    return {"n": 0, "correct": 0, "sum_change_pct": 0.0}


def _add(counter: dict, correct: bool, change_pct: float) -> None:
    counter["n"] += 1
    counter["correct"] += int(bool(correct))
    counter["sum_change_pct"] += change_pct


def _finalize(counter: dict) -> dict:
    n = counter["n"]
    correct = counter["correct"]
    early, actionable, strong, _, _ = _thresholds()
    if n == 0:
        return {
            "n": 0,
            "correct": 0,
            "raw_hit_rate_pct": None,
            "bayesian_hit_rate_pct": None,
            "wilson_lower_95_pct": None,
            "mean_change_pct": None,
            "sample_status": "INSUFFICIENT",
            "learning_weight": 0.0,
        }

    raw = correct / n
    bayes = (correct + PRIOR_ALPHA) / (n + PRIOR_ALPHA + PRIOR_BETA)
    wilson = _wilson_lower_bound(correct, n)

    if n >= actionable:
        sample_status = "ACTIONABLE"
        learning_weight = min(1.0, n / max(strong, 1))
    elif n >= early:
        sample_status = "EARLY_SIGNAL"
        learning_weight = min(0.35, n / max(strong, 1))
    else:
        sample_status = "INSUFFICIENT"
        learning_weight = 0.0

    return {
        "n": n,
        "correct": correct,
        "raw_hit_rate_pct": round(raw * 100.0, 2),
        "bayesian_hit_rate_pct": round(bayes * 100.0, 2),
        "wilson_lower_95_pct": None if wilson is None else round(wilson * 100.0, 2),
        "mean_change_pct": round(counter["sum_change_pct"] / n, 6),
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

    _, _, _, good, bad = _thresholds()
    rate = stats["bayesian_hit_rate_pct"]
    lower = stats["wilson_lower_95_pct"]
    if lower is not None and lower >= good:
        return "BOOST_CONFIDENCE"
    if rate is not None and rate <= bad:
        return "REDUCE_OR_AVOID"
    return "KEEP_NEUTRAL"


def main() -> int:
    predictions_root = ROOT / "data" / "predictions"
    evaluations_root = ROOT / "data" / "evaluations"
    out_root = ROOT / "data" / "statistics"
    out_root.mkdir(parents=True, exist_ok=True)

    predictions: dict[str, dict] = {}
    for path in predictions_root.rglob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            predictions[raw["prediction_id"]] = raw
        except Exception:
            continue

    by_instrument_category_horizon = defaultdict(_new_counter)
    by_instrument_horizon = defaultdict(_new_counter)
    by_category_horizon = defaultdict(_new_counter)
    by_confidence_horizon = defaultdict(_new_counter)
    by_score_type_horizon = defaultdict(_new_counter)
    by_context_horizon = defaultdict(_new_counter)
    by_context_signature_horizon = defaultdict(_new_counter)
    by_instrument_context_horizon = defaultdict(_new_counter)
    by_category_context_horizon = defaultdict(_new_counter)
    by_instrument_category_context_horizon = defaultdict(_new_counter)

    audit = {
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

        categories = prediction.get("categories") or ["UNKNOWN"]
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

                confidence_source = pred_item.get("next_session", {}) if horizon == "next_session" else pred_item.get("immediate", {})
                confidence_bucket = _confidence_bucket(confidence_source.get("confidence"))
                correct = bool(scored["correct"])
                change_pct = float(scored.get("change_pct", 0.0))
                score_type = scored.get("score_type", "directional")
                audit["scored_items"] += 1

                _add(by_instrument_horizon[(instrument, horizon)], correct, change_pct)
                _add(by_confidence_horizon[(confidence_bucket, horizon)], correct, change_pct)
                _add(by_score_type_horizon[(score_type, horizon)], correct, change_pct)

                for category in categories:
                    _add(by_category_horizon[(category, horizon)], correct, change_pct)
                    _add(by_instrument_category_horizon[(instrument, category, horizon)], correct, change_pct)

                if regimes:
                    audit["scored_items_with_context"] += 1
                    _add(by_context_signature_horizon[(signature, horizon)], correct, change_pct)
                    for context_name, regime in regimes.items():
                        _add(by_context_horizon[(context_name, regime, horizon)], correct, change_pct)
                        _add(by_instrument_context_horizon[(instrument, context_name, regime, horizon)], correct, change_pct)
                        for category in categories:
                            _add(by_category_context_horizon[(category, context_name, regime, horizon)], correct, change_pct)
                            _add(
                                by_instrument_category_context_horizon[(instrument, category, context_name, regime, horizon)],
                                correct,
                                change_pct,
                            )
                else:
                    audit["scored_items_without_context"] += 1

    def pack(mapping: dict, key_names: tuple[str, ...]) -> list[dict]:
        rows = []
        for key, counter in sorted(mapping.items(), key=lambda x: tuple(str(v) for v in x[0])):
            values = key if isinstance(key, tuple) else (key,)
            stats = _finalize(counter)
            row = {name: value for name, value in zip(key_names, values)}
            row.update(stats)
            row["recommendation"] = _recommendation(stats)
            rows.append(row)
        return rows

    early, actionable, strong, good, bad = _thresholds()
    profile = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "profile_version": "1.2.0",
        "purpose": "Evidence-based priors for future Forex Factory predictions. Never rewrite historical predictions.",
        "guardrails": {
            "minimum_sample_actionable": actionable,
            "minimum_sample_early_signal": early,
            "strong_sample": strong,
            "actionable_min_hit_rate_pct": good,
            "actionable_max_hit_rate_pct": bad,
            "bayesian_prior": {"alpha": PRIOR_ALPHA, "beta": PRIOR_BETA},
            "rule": "Only ACTIONABLE segments may materially change future confidence. EARLY_SIGNAL is advisory only; INSUFFICIENT causes no change.",
            "anti_overfit": "Use learned evidence as one input, not as a deterministic direction override. New macro facts and market context remain primary.",
            "anti_leakage": "Market context and evaluation anchors use only information available at or before the prediction decision time.",
        },
        "audit": audit,
        "confidence_calibration": pack(by_confidence_horizon, ("confidence_bucket", "horizon")),
        "by_instrument": pack(by_instrument_horizon, ("instrument", "horizon")),
        "by_category": pack(by_category_horizon, ("category", "horizon")),
        "by_score_type": pack(by_score_type_horizon, ("score_type", "horizon")),
        "by_instrument_category": pack(by_instrument_category_horizon, ("instrument", "category", "horizon")),
        "by_context": pack(by_context_horizon, ("context", "regime", "horizon")),
        "by_context_signature": pack(by_context_signature_horizon, ("context_signature", "horizon")),
        "by_instrument_context": pack(by_instrument_context_horizon, ("instrument", "context", "regime", "horizon")),
        "by_category_context": pack(by_category_context_horizon, ("category", "context", "regime", "horizon")),
        "by_instrument_category_context": pack(
            by_instrument_category_context_horizon,
            ("instrument", "category", "context", "regime", "horizon"),
        ),
    }

    out_path = out_root / "learning_profile.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
