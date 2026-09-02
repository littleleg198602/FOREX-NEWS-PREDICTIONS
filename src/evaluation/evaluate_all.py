from __future__ import annotations

import json
from pathlib import Path

from src.config import ROOT
from src.evaluation.evaluate_prediction import evaluate_prediction


def main() -> int:
    predictions_root = ROOT / "data" / "predictions"
    evaluations_root = ROOT / "data" / "evaluations"
    evaluations_root.mkdir(parents=True, exist_ok=True)

    processed = 0
    skipped = 0
    failed = 0

    for path in sorted(predictions_root.rglob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as f:
                raw = json.load(f)

            event_time = raw.get("event_time_utc") or raw.get("published_at_utc")
            if not event_time:
                print(f"[SKIP] {path}: missing event_time_utc/published_at_utc")
                skipped += 1
                continue

            output = evaluate_prediction(path)
            out_path = evaluations_root / f"{output['prediction_id']}.json"
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

    print(f"processed={processed} skipped={skipped} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
