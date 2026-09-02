from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
import math
import yaml

from src.config import ROOT
from src.market_data.context_snapshot import context_signature

HORIZONS = ("15m", "1h", "4h")
CONFIG_PATH = ROOT / "config" / "market_context.yaml"


def _load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _confidence_bucket(value) -> str:
    try:
        n = int(value)
    except Exception:
        return "UNKNOWN"
    if n <= 4:
        return "1-4"
    if n <= 6:
        return "5-6"
    if n <= 8:
        return "7-8"
    return "9-10"


def _segment_status(n: int, hit_rate: float | None, cfg: dict) -> str:
    learning = cfg.get("learning", {})
    early = int(learning.get("minimum_sample_early_signal", 10))
    actionable = int(learning.get("minimum_sample_actionable", 30))
    good = float(learning.get("actionable_min_hit_rate_pct", 58.0))
    bad = float(learning.get("actionable_max_hit_rate_pct", 42.0))

    if n < early:
        return "INSUFFICIENT"
    if n < actionable:
        return "EARLY_SIGNAL"
    if hit_rate is not None and (hit_rate >= good or hit_rate <= bad):
        return "ACTIONABLE"
    return "STABLE_NEUTRAL"


def _recommendation(status: str, hit_rate: float | None) -> str:
    if status != "ACTIONABLE" or hit_rate is None:
        return "NO_CONFIDENCE_CHANGE"
    if hit_rate >= 65:
        return "RAISE_CONFIDENCE_UP_TO_2"
    if hit_rate >= 58:
        return "RAISE_CONFIDENCE_UP_TO_1"
    if hit_rate <= 35:
        return "LOWER_CONFIDENCE_UP_TO_2"
    return "LOWER_CONFIDENCE_UP_TO_1"


def _wilson_lower(correct: int, n: int, z: float = 1.96) -> float | None:
    if n == 0:
        return None
    p = correct / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return ((centre - margin) / denom) * 100.0


def main() -> int:
    cfg = _load_config()
    predictions_root = ROOT / "data" / "predictions"
    evaluations_root = ROOT / "data" / "evaluations"
    out_root = ROOT / "data" / "statistics"
    out_root.mkdir(parents=True, exist_ok=True)

    prediction_meta = {}
    for path in predictions_root.rglob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            items = {item.get("instrument"): item for item in raw.get("predictions", [])}
            prediction_meta[raw["prediction_id"]] = {
                "categories": raw.get("categories", []) or ["UNKNOWN"],
                "items": items,
                "eligible": bool(raw.get("eligible_for_hit_rate", True)),
            }
        except Exception:
            continue

    segments = defaultdict(lambda: {"n": 0, "correct": 0, "sum_change": 0.0})
    audit = {
        "evaluation_files": 0,
        "eligible_evaluation_files": 0,
        "scored_items": 0,
        "context_missing_items": 0,
    }

    for path in evaluations_root.glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                ev = json.load(f)
        except Exception:
            continue

        audit["evaluation_files"] += 1
        pred = prediction_meta.get(ev.get("prediction_id"))
        if not pred or not pred["eligible"] or not bool(ev.get("eligible_for_hit_rate", True)):
            continue
        audit["eligible_evaluation_files"] += 1

        context = ev.get("market_context") or {}
        regimes = context.get("regimes", {})
        signature = context_signature(context)

        for result in ev.get("results", []):
            instrument = result.get("instrument", "UNKNOWN")
            pred_item = pred["items"].get(instrument, {})
            confidence = pred_item.get("immediate", {}).get("confidence", result.get("predicted_confidence"))
            conf_bucket = _confidence_bucket(confidence)

            for horizon in HORIZONS:
                item = result.get("evaluations", {}).get(horizon, {})
                if item.get("status") != "DONE" or item.get("correct") is None:
                    continue
                audit["scored_items"] += 1
                correct = bool(item["correct"])
                score_type = item.get("score_type", "directional")
                change = float(item.get("change_pct", 0.0))

                dimensions = [
                    ("GLOBAL", "ALL"),
                    ("INSTRUMENT", instrument),
                    ("CONFIDENCE", conf_bucket),
                    ("CONTEXT_SIGNATURE", signature),
                ]
                for category in pred["categories"]:
                    dimensions.append(("CATEGORY", category))
                    dimensions.append(("INSTRUMENT_CATEGORY", f"{instrument}|{category}"))
                    dimensions.append(("INSTRUMENT_CATEGORY_CONTEXT", f"{instrument}|{category}|{signature}"))

                if not regimes:
                    audit["context_missing_items"] += 1
                else:
                    for name, regime in regimes.items():
                        dimensions.append(("CONTEXT", f"{name}={regime}"))
                        dimensions.append(("INSTRUMENT_CONTEXT", f"{instrument}|{name}={regime}"))
                        for category in pred["categories"]:
                            dimensions.append(("CATEGORY_CONTEXT", f"{category}|{name}={regime}"))

                for dimension, key in dimensions:
                    segment_key = (dimension, key, horizon, score_type)
                    stats = segments[segment_key]
                    stats["n"] += 1
                    stats["correct"] += int(correct)
                    stats["sum_change"] += change

    rows = []
    for (dimension, key, horizon, score_type), stats in segments.items():
        n = stats["n"]
        hit_rate = round((stats["correct"] / n) * 100.0, 2) if n else None
        status = _segment_status(n, hit_rate, cfg)
        rows.append({
            "dimension": dimension,
            "key": key,
            "horizon": horizon,
            "score_type": score_type,
            "n": n,
            "correct": stats["correct"],
            "hit_rate_pct": hit_rate,
            "wilson_lower_95_pct": None if n == 0 else round(_wilson_lower(stats["correct"], n), 2),
            "mean_change_pct": None if n == 0 else round(stats["sum_change"] / n, 6),
            "status": status,
            "recommendation": _recommendation(status, hit_rate),
        })

    rows.sort(key=lambda x: (x["status"] != "ACTIONABLE", -x["n"], x["dimension"], x["key"], x["horizon"]))

    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "methodology": {
            "principle": "Only ex-ante eligible predictions are learned from; context uses information available at or before event time.",
            "confidence_policy": "Only ACTIONABLE segments may change confidence. EARLY_SIGNAL is advisory. INSUFFICIENT and STABLE_NEUTRAL do not change confidence.",
            "anti_overfit": cfg.get("learning", {}),
        },
        "audit": audit,
        "actionable_segments": [row for row in rows if row["status"] == "ACTIONABLE"],
        "early_signal_segments": [row for row in rows if row["status"] == "EARLY_SIGNAL"],
        "all_segments": rows,
    }

    out_path = out_root / "learning_profile.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
