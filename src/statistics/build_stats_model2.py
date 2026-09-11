from __future__ import annotations

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
