from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json

from src.config import ROOT, load_evaluation_config
from src.prediction.normalization import normalize_prediction

HORIZONS = ("15m", "1h", "4h", "next_session")
SCORE_TYPES = ("directional", "mixed_neutral", "volatility")
EVAL_CONFIG = load_evaluation_config()


def _safe_rate(correct: int, scored: int) -> float | None:
    if scored == 0:
        return None
    return round((correct / scored) * 100.0, 2)


def _empty_block() -> dict:
    return {h: {"scored": 0, "correct": 0, "sum_change_pct": 0.0} for h in HORIZONS}


def _empty_score_blocks() -> dict:
    return {score_type: _empty_block() for score_type in SCORE_TYPES}


def _finalize(block: dict) -> dict:
    out = {}
    for horizon, stats in block.items():
        scored = stats["scored"]
        out[horizon] = {
            "n": scored,
            "correct": stats["correct"],
            "hit_rate_pct": _safe_rate(stats["correct"], scored),
            "mean_change_pct": None if scored == 0 else round(stats["sum_change_pct"] / scored, 6),
        }
    return out


def _finalize_score_blocks(score_blocks: dict) -> dict:
    return {score_type: _finalize(block) for score_type, block in score_blocks.items()}


def _combine_score_types(finalized_by_score_type: dict) -> dict:
    """Diagnostic-only combined score; never call this directional accuracy."""
    combined = {}
    for horizon in HORIZONS:
        n = 0
        correct = 0
        by_type = {}
        for score_type in SCORE_TYPES:
            item = finalized_by_score_type.get(score_type, {}).get(horizon, {})
            type_n = int(item.get("n", 0) or 0)
            type_correct = int(item.get("correct", 0) or 0)
            n += type_n
            correct += type_correct
            by_type[score_type] = {
                "n": type_n,
                "correct": type_correct,
                "hit_rate_pct": item.get("hit_rate_pct"),
            }
        combined[horizon] = {
            "n": n,
            "correct": correct,
            "hit_rate_pct": _safe_rate(correct, n),
            "by_score_type": by_type,
            "interpretation": "diagnostic_only_not_directional_accuracy",
        }
    return combined


def _write_daily_performance_snapshot(
    out_root,
    generated_at: datetime,
    audit: dict,
    directional: dict,
    overall_combined: dict,
) -> None:
    history_path = out_root / "performance_history.json"
    history = {
        "scope": "daily UTC snapshots of leakage-safe evaluation v2; directional is primary, combined is diagnostic only",
        "snapshots": [],
    }
    if history_path.exists():
        try:
            with history_path.open("r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict) and isinstance(loaded.get("snapshots"), list):
                history = loaded
        except Exception:
            pass

    today = generated_at.date().isoformat()
    snapshot = {
        "date_utc": today,
        "generated_at_utc": generated_at.isoformat(),
        "evaluation_version": EVAL_CONFIG.get("evaluation_version"),
        "eligible_prediction_files": audit.get("eligible_prediction_files", 0),
        "directional_primary": directional,
        "overall_combined_diagnostic": overall_combined,
    }

    snapshots = [row for row in history.get("snapshots", []) if row.get("date_utc") != today]
    snapshots.append(snapshot)
    snapshots.sort(key=lambda row: row.get("date_utc", ""))
    history["snapshots"] = snapshots[-365:]

    with history_path.open("w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def main() -> int:
    evaluations_root = ROOT / EVAL_CONFIG.get("output", {}).get("evaluations_dir", "data/evaluations_v2")
    predictions_root = ROOT / "data" / "predictions"
    out_root = ROOT / EVAL_CONFIG.get("output", {}).get("statistics_dir", "data/statistics_v2")
    out_root.mkdir(parents=True, exist_ok=True)

    prediction_meta: dict[str, dict] = {}
    for path in predictions_root.rglob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            normalized = normalize_prediction(raw)
            prediction_meta[normalized["prediction_id"]] = {
                "categories": normalized.get("categories", ["UNKNOWN"]),
                "eligible_for_hit_rate": bool(normalized.get("eligible_for_hit_rate", True)),
                "backfilled": bool(normalized.get("backfilled", False)),
                "is_example": bool(normalized.get("is_example", False)),
                "model_version": normalized.get("model_version") or "UNKNOWN",
            }
        except Exception:
            continue

    overall_by_score_type = _empty_score_blocks()
    by_model_version = defaultdict(_empty_score_blocks)
    by_instrument = defaultdict(lambda: defaultdict(_empty_score_blocks))
    by_category = defaultdict(lambda: defaultdict(_empty_score_blocks))
    audit = {
        "evaluation_version": EVAL_CONFIG.get("evaluation_version"),
        "evaluation_files": 0,
        "eligible_prediction_files": 0,
        "excluded_backfilled_or_ineligible": 0,
        "excluded_examples": 0,
        "unscored_done_items": 0,
        "market_closed_items": 0,
        "data_gap_items": 0,
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
        meta = prediction_meta.get(prediction_id, {})
        if bool(evaluation.get("is_example", meta.get("is_example", False))):
            audit["excluded_examples"] += 1
            continue

        eligible = bool(evaluation.get("eligible_for_hit_rate", meta.get("eligible_for_hit_rate", True)))
        if not eligible or bool(meta.get("backfilled", False)):
            audit["excluded_backfilled_or_ineligible"] += 1
            continue

        audit["eligible_prediction_files"] += 1
        categories = meta.get("categories", []) or ["UNKNOWN"]
        model_version = str(evaluation.get("model_version") or meta.get("model_version") or "UNKNOWN")

        for result in evaluation.get("results", []):
            instrument = result.get("instrument", "UNKNOWN")
            evaluations = result.get("evaluations", {})
            for horizon in HORIZONS:
                item = evaluations.get(horizon, {})
                status = item.get("status")
                if status == "MARKET_CLOSED":
                    audit["market_closed_items"] += 1
                    continue
                if status == "DATA_GAP":
                    audit["data_gap_items"] += 1
                    continue
                if status != "DONE":
                    continue

                correct = item.get("correct")
                score_type = item.get("score_type", "directional")
                if correct is None or score_type not in SCORE_TYPES:
                    audit["unscored_done_items"] += 1
                    continue

                change_pct = float(item.get("change_pct", 0.0))
                targets = [
                    overall_by_score_type[score_type][horizon],
                    by_model_version[model_version][score_type][horizon],
                    by_instrument[model_version][instrument][score_type][horizon],
                ]
                for category in categories:
                    targets.append(by_category[model_version][category][score_type][horizon])

                for stats in targets:
                    stats["scored"] += 1
                    stats["correct"] += int(bool(correct))
                    stats["sum_change_pct"] += change_pct

    generated_at = datetime.now(timezone.utc)
    finalized_overall = _finalize_score_blocks(overall_by_score_type)
    directional_primary = finalized_overall["directional"]
    overall_combined = _combine_score_types(finalized_overall)

    summary = {
        "generated_at_utc": generated_at.isoformat(),
        "evaluation_version": EVAL_CONFIG.get("evaluation_version"),
        "scope": "eligible ex-ante predictions only; leakage-safe fixed horizons; directional accuracy is primary; MIXED/VOLATILITY separate",
        "audit": audit,
        "directional_primary": directional_primary,
        "overall_by_score_type": finalized_overall,
        "overall_combined_diagnostic": overall_combined,
        "by_model_version": {
            version: _finalize_score_blocks(score_blocks)
            for version, score_blocks in sorted(by_model_version.items())
        },
        "by_instrument": {
            version: {
                instrument: _finalize_score_blocks(score_blocks)
                for instrument, score_blocks in sorted(instruments.items())
            }
            for version, instruments in sorted(by_instrument.items())
        },
        "by_category": {
            version: {
                category: _finalize_score_blocks(score_blocks)
                for category, score_blocks in sorted(categories.items())
            }
            for version, categories in sorted(by_category.items())
        },
    }

    out_path = out_root / "summary.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    _write_daily_performance_snapshot(out_root, generated_at, audit, directional_primary, overall_combined)

    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
