from __future__ import annotations

import json
from pathlib import Path

from src.config import ROOT
from src.evaluation.evaluate_prediction import evaluate_prediction

REQUIRED_HORIZONS = ("15m", "1h", "4h", "next_session")
TERMINAL_HORIZON_STATES = {"DONE", "NOT_PREDICTED"}


def _existing_evaluation_complete(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return False

    results = raw.get("results", [])
    if not results:
        return False
    for result in results:
        evaluations = result.get("evaluations", {})
        for horizon in REQUIRED_HORIZONS:
            if evaluations.get(horizon, {}).get("status") not in TERMINAL_HORIZON_STATES:
                return False
    return True


def main() -> int:
    predictions_root = ROOT / "data" / "predictions"
    evaluations_root = ROOT / "data" / "evaluations"
    evaluations_root.mkdir(parents=True, exist_ok=True)

    processed = 0
    skipped = 0
    complete = 0
    failed = 0

    for path in sorted(predictions_root.rglob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as f:
                raw = json.load(f)

            if bool(raw.get("is_example", False)):
                print(f"[SKIP] {path}: example/test fixture")
                skipped += 1
                continue

            event_time = raw.get("event_time_utc") or raw.get("published_at_utc")
            if not event_time:
                print(f"[SKIP] {path}: missing event_time_utc/published_at_utc")
                skipped += 1
                continue

            prediction_id = raw["prediction_id"]
            out_path = evaluations_root / f"{prediction_id}.json"
            if _existing_evaluation_complete(out_path):
                print(f"[DONE] {path}: all evaluation horizons already complete")
                complete += 1
                continue

            output = evaluate_prediction(path)
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)

            done = sum(
                1
                for result in output.get("results", [])
                for item in result.get("evaluations", {}).values()
                if isinstance(item, dict) and item.get("status") == "DONE"
            )
            print(f"[OK] {path} -> {out_path} ({done} completed horizons)")
            processed += 1
        except Exception as exc:
            print(f"[FAIL] {path}: {type(exc).__name__}: {exc}")
            failed += 1

    print(f"processed={processed} complete={complete} skipped={skipped} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
