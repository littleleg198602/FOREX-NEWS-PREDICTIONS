from __future__ import annotations

import json
import os
from pathlib import Path
import time

from src.config import ROOT, load_evaluation_config, load_instruments
from src.evaluation.evaluate_prediction import evaluate_prediction
from src.prediction.normalization import normalize_prediction, validate_normalized_prediction

REQUIRED_HORIZONS = ("15m", "1h", "4h", "next_session")
TERMINAL_HORIZON_STATES = {"DONE", "NOT_PREDICTED", "MARKET_CLOSED"}
RETRYABLE_RESULT_STATES = {"PROVIDER_ERROR", "NO_REFERENCE_PRICE", "DATA_GAP", "PENDING", "PARTIAL"}
EVAL_CONFIG = load_evaluation_config()


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _existing_evaluation_complete(path: Path) -> bool:
    raw = _load_json(path)
    if not raw or raw.get("evaluation_version") != EVAL_CONFIG.get("evaluation_version"):
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


def _merge_result(existing: dict | None, new: dict) -> dict:
    if not existing:
        return new

    # If a later provider attempt fails entirely, keep the previously captured
    # reference and completed horizons. A transient outage must never erase DONE.
    if new.get("status") in {"PROVIDER_ERROR", "NO_REFERENCE_PRICE"}:
        preserved = dict(existing)
        preserved["last_retry_status"] = new.get("status")
        if new.get("provider_error"):
            preserved["last_provider_error"] = new.get("provider_error")
        return preserved

    merged = dict(existing)
    for key, value in new.items():
        if key != "evaluations":
            merged[key] = value

    old_evaluations = existing.get("evaluations", {})
    new_evaluations = new.get("evaluations", {})
    combined: dict[str, dict] = {}
    for horizon in set(old_evaluations) | set(new_evaluations):
        old_item = old_evaluations.get(horizon)
        new_item = new_evaluations.get(horizon)
        if isinstance(old_item, dict) and old_item.get("status") in TERMINAL_HORIZON_STATES:
            combined[horizon] = old_item
        elif isinstance(new_item, dict):
            combined[horizon] = new_item
        elif isinstance(old_item, dict):
            combined[horizon] = old_item
    merged["evaluations"] = combined

    statuses = [value.get("status") for value in combined.values() if isinstance(value, dict)]
    if statuses and all(status in TERMINAL_HORIZON_STATES for status in statuses):
        merged["status"] = "DONE"
    elif any(status == "DONE" for status in statuses):
        merged["status"] = "PARTIAL"
    elif merged.get("status") not in RETRYABLE_RESULT_STATES:
        merged["status"] = "PENDING"
    return merged


def _merge_evaluation(existing: dict | None, new: dict) -> dict:
    if not existing:
        return new

    merged = dict(existing)
    for key, value in new.items():
        if key != "results":
            # Preserve an already captured usable context if a retry can only
            # provide an empty/UNKNOWN reconstruction.
            if key == "market_context":
                old_regimes = existing.get("market_context", {}).get("regimes", {})
                new_regimes = value.get("regimes", {}) if isinstance(value, dict) else {}
                old_usable = any(v and v != "UNKNOWN" for v in old_regimes.values())
                new_usable = any(v and v != "UNKNOWN" for v in new_regimes.values())
                if old_usable and not new_usable:
                    continue
            merged[key] = value

    old_by_instrument = {
        item.get("instrument"): item
        for item in existing.get("results", [])
        if isinstance(item, dict) and item.get("instrument")
    }
    new_by_instrument = {
        item.get("instrument"): item
        for item in new.get("results", [])
        if isinstance(item, dict) and item.get("instrument")
    }
    order: list[str] = []
    for item in new.get("results", []) + existing.get("results", []):
        instrument = item.get("instrument") if isinstance(item, dict) else None
        if instrument and instrument not in order:
            order.append(instrument)

    merged_results: list[dict] = []
    for instrument in order:
        old_item = old_by_instrument.get(instrument)
        new_item = new_by_instrument.get(instrument)
        if new_item is None and old_item is not None:
            merged_results.append(old_item)
        elif new_item is not None:
            merged_results.append(_merge_result(old_item, new_item))
    merged["results"] = merged_results
    return merged


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


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
            if _existing_evaluation_complete(out_path):
                print(f"[DONE] {path}: all v2 evaluation horizons already terminal")
                complete += 1
                continue

            existing = _load_json(out_path)
            output = _evaluate_with_retry(path)
            merged = _merge_evaluation(existing, output)
            _atomic_write_json(out_path, merged)

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
