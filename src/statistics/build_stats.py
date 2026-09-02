from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path

from src.config import ROOT

HORIZONS = ("15m", "1h", "4h")


def _safe_rate(correct: int, scored: int) -> float | None:
    if scored == 0:
        return None
    return round((correct / scored) * 100.0, 2)


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

    totals = {h: {"scored": 0, "correct": 0, "sum_change_pct": 0.0} for h in HORIZONS}
    by_instrument = defaultdict(lambda: {h: {"scored": 0, "correct": 0, "sum_change_pct": 0.0} for h in HORIZONS})
    by_category = defaultdict(lambda: {h: {"scored": 0, "correct": 0, "sum_change_pct": 0.0} for h in HORIZONS})
    audit = {"evaluation_files": 0, "eligible_prediction_files": 0, "excluded_backfilled_or_ineligible": 0}

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
                if correct is None:
                    continue
                change_pct = float(item.get("change_pct", 0.0))

                totals[horizon]["scored"] += 1
                totals[horizon]["correct"] += int(bool(correct))
                totals[horizon]["sum_change_pct"] += change_pct

                by_instrument[instrument][horizon]["scored"] += 1
                by_instrument[instrument][horizon]["correct"] += int(bool(correct))
                by_instrument[instrument][horizon]["sum_change_pct"] += change_pct

                for category in categories:
                    by_category[category][horizon]["scored"] += 1
                    by_category[category][horizon]["correct"] += int(bool(correct))
                    by_category[category][horizon]["sum_change_pct"] += change_pct

    def finalize(block: dict) -> dict:
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

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "eligible_for_hit_rate only; MIXED/VOLATILITY are currently unscored",
        "audit": audit,
        "overall": finalize(totals),
        "by_instrument": {name: finalize(block) for name, block in sorted(by_instrument.items())},
        "by_category": {name: finalize(block) for name, block in sorted(by_category.items())},
    }

    out_path = out_root / "summary.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
