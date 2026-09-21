from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json

from src.config import ROOT, load_evaluation_config
from src.statistics import build_stats as legacy

EVAL_CONFIG = load_evaluation_config()
HORIZONS = ("15m", "1h", "4h", "next_session")
SCORE_TYPES = ("directional", "mixed_neutral", "volatility")


def _coverage(score_blocks: dict) -> dict:
    out = {}
    for horizon in HORIZONS:
        counts = {
            score_type: int(score_blocks.get(score_type, {}).get(horizon, {}).get("n", 0) or 0)
            for score_type in SCORE_TYPES
        }
        total = sum(counts.values())
        directional = counts["directional"]
        out[horizon] = {
            "directional_n": directional,
            "all_scored_n": total,
            "coverage_pct": None if total == 0 else round(directional / total * 100.0, 2),
            "non_directional_n": total - directional,
        }
    return out


def _counting_audit() -> tuple[dict, dict]:
    evaluations_root = ROOT / EVAL_CONFIG.get("output", {}).get("evaluations_dir", "data/evaluations_v2")
    by_model: dict[str, dict] = {}
    event_ids_by_model: dict[str, set[str]] = defaultdict(set)
    paired_index: dict[tuple[str, str, str], dict[str, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )

    def model_bucket(model_version: str) -> dict:
        if model_version not in by_model:
            by_model[model_version] = {
                "evaluation_files": 0,
                "eligible_evaluation_files": 0,
                "excluded_ineligible_or_backfilled": 0,
                "independent_event_count": 0,
                "horizons": {
                    horizon: {
                        "items_total": 0,
                        "done": 0,
                        "scored": 0,
                        "directional": 0,
                        "mixed_neutral": 0,
                        "volatility": 0,
                        "done_unscored": 0,
                        "market_closed": 0,
                        "data_gap": 0,
                        "not_predicted": 0,
                        "pending": 0,
                        "provider_error": 0,
                        "no_reference_price": 0,
                        "missing": 0,
                        "other": 0,
                    }
                    for horizon in HORIZONS
                },
            }
        return by_model[model_version]

    for path in evaluations_root.glob("*.json"):
        try:
            evaluation = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if evaluation.get("evaluation_version") != EVAL_CONFIG.get("evaluation_version"):
            continue

        model_version = str(evaluation.get("model_version") or "UNKNOWN")
        bucket = model_bucket(model_version)
        bucket["evaluation_files"] += 1

        eligible = bool(evaluation.get("eligible_for_hit_rate", True))
        if not eligible or bool(evaluation.get("backfilled", False)) or bool(evaluation.get("is_example", False)):
            bucket["excluded_ineligible_or_backfilled"] += 1
            continue

        bucket["eligible_evaluation_files"] += 1
        event_id = str(evaluation.get("event_id") or evaluation.get("prediction_id") or path.stem)
        event_ids_by_model[model_version].add(event_id)

        for result in evaluation.get("results", []):
            if not isinstance(result, dict):
                continue
            instrument = str(result.get("instrument") or "UNKNOWN")
            evaluations = result.get("evaluations", {})
            for horizon in HORIZONS:
                item = evaluations.get(horizon, {})
                horizon_counts = bucket["horizons"][horizon]
                horizon_counts["items_total"] += 1
                if not isinstance(item, dict) or not item:
                    horizon_counts["missing"] += 1
                    continue
                status = str(item.get("status") or "UNKNOWN").upper()

                if status == "DONE":
                    horizon_counts["done"] += 1
                    correct = item.get("correct")
                    score_type = str(item.get("score_type") or "directional")
                    if correct is not None and score_type in SCORE_TYPES:
                        horizon_counts["scored"] += 1
                        horizon_counts[score_type] += 1
                    else:
                        horizon_counts["done_unscored"] += 1
                elif status == "MARKET_CLOSED":
                    horizon_counts["market_closed"] += 1
                elif status == "DATA_GAP":
                    horizon_counts["data_gap"] += 1
                elif status == "NOT_PREDICTED":
                    horizon_counts["not_predicted"] += 1
                elif status == "PENDING":
                    horizon_counts["pending"] += 1
                elif status == "PROVIDER_ERROR":
                    horizon_counts["provider_error"] += 1
                elif status == "NO_REFERENCE_PRICE":
                    horizon_counts["no_reference_price"] += 1
                else:
                    horizon_counts["other"] += 1

                if model_version in {"1.1.1", "2.0.0"}:
                    paired_index[(event_id, instrument, horizon)][model_version].append(
                        {
                            "status": status,
                            "correct": item.get("correct"),
                            "score_type": item.get("score_type"),
                        }
                    )

    for model_version, event_ids in event_ids_by_model.items():
        model_bucket(model_version)["independent_event_count"] = len(event_ids)

    paired_events = event_ids_by_model.get("1.1.1", set()) & event_ids_by_model.get("2.0.0", set())
    pair_horizons = {
        horizon: {
            "matched_items": 0,
            "both_scored": 0,
            "both_directional": 0,
            "m1_directional": 0,
            "m1_directional_correct": 0,
            "m2_directional": 0,
            "m2_directional_correct": 0,
            "score_type_combinations": {},
        }
        for horizon in HORIZONS
    }
    ambiguous_pairs = 0

    for (_, _, horizon), versions in paired_index.items():
        if "1.1.1" not in versions or "2.0.0" not in versions:
            continue
        if len(versions["1.1.1"]) != 1 or len(versions["2.0.0"]) != 1:
            ambiguous_pairs += 1
            continue

        m1 = versions["1.1.1"][0]
        m2 = versions["2.0.0"][0]
        row = pair_horizons[horizon]
        row["matched_items"] += 1

        m1_scored = m1["status"] == "DONE" and m1["correct"] is not None and m1["score_type"] in SCORE_TYPES
        m2_scored = m2["status"] == "DONE" and m2["correct"] is not None and m2["score_type"] in SCORE_TYPES
        if m1_scored and m2_scored:
            row["both_scored"] += 1
            combo = f'{m1["score_type"]}->{m2["score_type"]}'
            row["score_type_combinations"][combo] = row["score_type_combinations"].get(combo, 0) + 1

        if m1_scored and m1["score_type"] == "directional":
            row["m1_directional"] += 1
            row["m1_directional_correct"] += int(bool(m1["correct"]))
        if m2_scored and m2["score_type"] == "directional":
            row["m2_directional"] += 1
            row["m2_directional_correct"] += int(bool(m2["correct"]))
        if (
            m1_scored
            and m2_scored
            and m1["score_type"] == "directional"
            and m2["score_type"] == "directional"
        ):
            row["both_directional"] += 1

    for row in pair_horizons.values():
        row["m1_directional_hit_rate_pct"] = (
            None
            if row["m1_directional"] == 0
            else round(row["m1_directional_correct"] / row["m1_directional"] * 100.0, 2)
        )
        row["m2_directional_hit_rate_pct"] = (
            None
            if row["m2_directional"] == 0
            else round(row["m2_directional_correct"] / row["m2_directional"] * 100.0, 2)
        )

    paired = {
        "models": ["1.1.1", "2.0.0"],
        "paired_independent_event_count": len(paired_events),
        "ambiguous_duplicate_item_pairs_skipped": ambiguous_pairs,
        "by_horizon": pair_horizons,
        "pairing_key": "event_id + instrument + horizon; only unique one-to-one M1/M2 items are paired",
    }
    return dict(sorted(by_model.items())), paired


def main() -> int:
    rc = legacy.main()
    if rc:
        return rc

    out_root = ROOT / EVAL_CONFIG.get("output", {}).get("statistics_dir", "data/statistics_v2")
    summary_path = out_root / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["directional_coverage"] = _coverage(summary.get("overall_by_score_type", {}))
    summary["quality_reporting_rule"] = (
        "Directional accuracy must always be shown together with directional coverage; "
        "a higher hit rate caused only by replacing directional calls with MIXED is not model improvement."
    )

    for model_version, score_blocks in summary.get("by_model_version", {}).items():
        if isinstance(score_blocks, dict):
            score_blocks["directional_coverage"] = _coverage(score_blocks)

    counting_audit, paired = _counting_audit()
    summary["counting_audit_by_model_version"] = counting_audit
    summary["independent_event_count_by_model_version"] = {
        model_version: details["independent_event_count"]
        for model_version, details in counting_audit.items()
    }
    summary["paired_m1_m2"] = paired
    summary["counting_explanation"] = (
        "Only DONE items with non-null correct and a recognized score_type are scored. "
        "MARKET_CLOSED, DATA_GAP, NOT_PREDICTED, PENDING, PROVIDER_ERROR and NO_REFERENCE_PRICE "
        "remain visible in counting_audit_by_model_version but are not wins or losses."
    )

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    history_path = out_root / "performance_history.json"
    if history_path.exists():
        history = json.loads(history_path.read_text(encoding="utf-8"))
        today = datetime.now(timezone.utc).date().isoformat()
        for snapshot in history.get("snapshots", []):
            if snapshot.get("date_utc") == today:
                snapshot["directional_coverage"] = summary["directional_coverage"]
                snapshot["quality_reporting_rule"] = summary["quality_reporting_rule"]
        history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
