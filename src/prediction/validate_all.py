from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from src.config import ROOT, load_instruments
from src.prediction.normalization import normalize_prediction, validate_normalized_prediction

SCHEMA_PATH = ROOT / "schemas" / "prediction.schema.json"


def _load_schema() -> dict:
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    predictions_root = ROOT / "data" / "predictions"
    out_root = ROOT / "data" / "statistics_v2"
    out_root.mkdir(parents=True, exist_ok=True)

    validator = Draft202012Validator(_load_schema(), format_checker=FormatChecker())
    known_instruments = set(load_instruments())

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "schema": "prediction_v2_normalized",
        "total_files": 0,
        "examples": 0,
        "valid": 0,
        "valid_after_legacy_adaptation": 0,
        "quarantined_legacy_ineligible": 0,
        "hard_failures": 0,
        "records": [],
    }

    for path in sorted(predictions_root.rglob("*.json")):
        report["total_files"] += 1
        relative_path = str(path.relative_to(ROOT))
        try:
            with path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as exc:
            report["hard_failures"] += 1
            report["records"].append({
                "path": relative_path,
                "status": "HARD_FAIL",
                "errors": [f"invalid JSON: {type(exc).__name__}: {exc}"],
            })
            continue

        if bool(raw.get("is_example", False)):
            report["examples"] += 1
            report["records"].append({"path": relative_path, "status": "EXAMPLE"})
            continue

        normalized = normalize_prediction(raw)
        errors, warnings = validate_normalized_prediction(normalized, known_instruments)
        schema_errors = sorted(validator.iter_errors(normalized), key=lambda err: list(err.absolute_path))
        errors.extend(
            f"schema {'.'.join(str(v) for v in err.absolute_path) or '<root>'}: {err.message}"
            for err in schema_errors
        )
        errors = sorted(set(errors))
        warnings = sorted(set(warnings))

        if errors:
            legacy_ineligible = bool(normalized.get("backfilled", False)) or not bool(normalized.get("eligible_for_hit_rate", True))
            status = "QUARANTINED_LEGACY_INELIGIBLE" if legacy_ineligible else "HARD_FAIL"
            if legacy_ineligible:
                report["quarantined_legacy_ineligible"] += 1
            else:
                report["hard_failures"] += 1
            report["records"].append({
                "path": relative_path,
                "prediction_id": normalized.get("prediction_id"),
                "status": status,
                "errors": errors,
                "warnings": warnings,
            })
            continue

        if warnings:
            report["valid_after_legacy_adaptation"] += 1
            status = "VALID_ADAPTED"
        else:
            report["valid"] += 1
            status = "VALID"
        report["records"].append({
            "path": relative_path,
            "prediction_id": normalized.get("prediction_id"),
            "status": status,
            "warnings": warnings,
        })

    out_path = out_root / "data_health.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(
        "prediction_validation "
        f"total={report['total_files']} valid={report['valid']} "
        f"adapted={report['valid_after_legacy_adaptation']} "
        f"legacy_quarantine={report['quarantined_legacy_ineligible']} "
        f"hard_failures={report['hard_failures']}"
    )
    print(out_path)
    return 1 if report["hard_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
