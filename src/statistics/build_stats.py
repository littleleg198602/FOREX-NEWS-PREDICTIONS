from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json

from src.config import ROOT

HORIZONS = ("15m", "1h", "4h")
SCORE_TYPES = ("directional", "mixed_neutral", "volatility")


def _safe_rate(correct: int, scored: int) -> float | None:
    if scored == 0:
        return None
    return round((correct / scored) * 100.0, 2)


def _empty_block() -> dict:
    return {h: {"scored": 0, "correct": 0, "sum_change_pct": 0.0} for h in HORIZONS}


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


def main() -> int:
    evaluations_root = ROOT / "data" / "evaluations"
    predictions_root = ROOT / "data" / "predictions"
    out_root = ROOT / "data" / "statistics"
    out_root.mkdir(parents=True, exist_ok=True)

    prediction_meta: dict[str, dict] = {}
    for path in predictions_root.rglob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            prediction_meta[raw["prediction_id"]] = {
                "categories": raw.get("categories", []),
                "eligible_for_hit_rate": bool(raw.get("eligible_for_hit_rate", True)),
                "backfilled": bool(raw.get("backfilled", False)),
            }
        except Exception:
            continue

    overall_by_score_type = {score_type: _empty_block() for score_type in SCORE_TYPES}
    by_instrument = defaultdict(lambda: {score_type: _empty_block() for score_type in SCORE_TYPES})
    by_category = defaultdict(lambda: {score_type: _empty_block() for score_type in SCORE_TYPES})
    audit = {
        "evaluation_files": 0,
        "eligible_prediction_files": 0,
        "excluded_backfilled_or_ineligible": 0,
        "unscored_done_items": 0,
    }

    for path in evaluations_root.glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                evaluation = json.load(f)
        except Exception:
            continue

        audit["evaluation_files"] += 1
        prediction_id = evaluation.get("prediction_id")
        meta = prediction_meta.get(prediction_id, {})
        eligible = bool(evaluation.get("eligible_for_hit_rate", meta.get("eligible_for_hit_rate", True)))
        if not eligible:
            audit["excluded_backfilled_or_ineligible"] += 1
            continue

        audit["eligible_prediction_files"] += 1
        categories = meta.get("categories", []) or ["UNKNOWN"]

        for result in evaluation.get("results", []):
            instrument = result.get("instrument", "UNKNOWN")
            evaluations = result.get("evaluations", {})
            for horizon in HORIZONS:
                item = evaluations.get(horizon, {})
                if item.get("status") != "DONE":
                    continue

                correct = item.get("correct")
                score_type = item.get("score_type", "directional")
                if correct is None or score_type not in SCORE_TYPES:
                    audit["unscored_done_items"] += 1
                    continue

                change_pct = float(item.get("change_pct", 0.0))

                targets = [
                    overall_by_score_type[score_type][horizon],
                    by_instrument[instrument][score_type][horizon],
                ]
                for category in categories:
                    targets.append(by_category[category][score_type][horizon])

                for stats in targets:
                    stats["scored"] += 1
                    stats["correct"] += int(bool(correct))
                    stats["sum_change_pct"] += change_pct

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "eligible_for_hit_rate only; directional, MIXED and VOLATILITY are reported separately",
        "audit": audit,
        "overall_by_score_type": {
            score_type: _finalize(block)
            for score_type, block in overall_by_score_type.items()
        },
        "by_instrument": {
            name: {score_type: _finalize(block) for score_type, block in score_blocks.items()}
            for name, score_blocks in sorted(by_instrument.items())
        },
        "by_category": {
            name: {score_type: _finalize(block) for score_type, block in score_blocks.items()}
            for name, score_blocks in sorted(by_category.items())
        },
    }

    out_path = out_root / "summary.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
