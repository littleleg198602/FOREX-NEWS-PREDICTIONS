from __future__ import annotations

import json
from pathlib import Path
import time

from src.config import ROOT, load_evaluation_config, load_instruments
from src.evaluation import evaluate_all as legacy_batch
from src.evaluation.evaluate_prediction_model2 import evaluate_prediction
from src.prediction.normalization import normalize_prediction, validate_normalized_prediction

EVAL_CONFIG = load_evaluation_config()


def _evaluate_with_retry(path: Path, attempts: int = 3) -> dict:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            output = evaluate_prediction(path)
            if not any(result.get("status") == "PROVIDER_ERROR" for result in output.get("results", [])):
                return output
            last_error = RuntimeError("one or more instruments returned PROVIDER_ERROR")
        except Exception as exc:
            last_error = exc
        if attempt < attempts:
            time.sleep(attempt * 2)
    if last_error:
        raise last_error
    raise RuntimeError("evaluation retry loop ended unexpectedly")


def main() -> int:
    predictions_root = ROOT / "data" / "predictions"
    evaluations_root = ROOT / EVAL_CONFIG.get("output", {}).get("evaluations_dir", "data/evaluations_v2")
    evaluations_root.mkdir(parents=True, exist_ok=True)

    processed = 0
    skipped = 0
    complete = 0
    quarantined = 0
    failed = 0
    known_instruments = set(load_instruments())

    for path in sorted(predictions_root.rglob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as f:
                raw = json.load(f)

            if bool(raw.get("is_example", False)):
                print(f"[SKIP] {path}: example/test fixture")
                skipped += 1
                continue

            normalized = normalize_prediction(raw)
            errors, warnings = validate_normalized_prediction(normalized, known_instruments)
            if errors:
                if bool(normalized.get("backfilled", False)) or not bool(normalized.get("eligible_for_hit_rate", True)):
                    print(f"[QUARANTINE] {path}: {'; '.join(errors)}")
                    quarantined += 1
                    continue
                raise ValueError("; ".join(errors))

            if warnings:
                print(f"[ADAPT] {path}: {'; '.join(warnings)}")

            prediction_id = normalized["prediction_id"]
            out_path = evaluations_root / f"{prediction_id}.json"
            if legacy_batch._existing_evaluation_complete(out_path):
                print(f"[DONE] {path}: all v2 evaluation horizons already terminal")
                complete += 1
                continue

            existing = legacy_batch._load_json(out_path)
            output = _evaluate_with_retry(path)
            merged = legacy_batch._merge_evaluation(existing, output)
            legacy_batch._atomic_write_json(out_path, merged)

            done = sum(
                1
                for result in merged.get("results", [])
                for item in result.get("evaluations", {}).values()
                if isinstance(item, dict) and item.get("status") == "DONE"
            )
            print(f"[OK] {path} -> {out_path} ({done} completed v2 horizons)")
            processed += 1
        except Exception as exc:
            print(f"[FAIL] {path}: {type(exc).__name__}: {exc}")
            failed += 1

    print(
        f"processed={processed} complete={complete} skipped={skipped} "
        f"quarantined={quarantined} failed={failed}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
