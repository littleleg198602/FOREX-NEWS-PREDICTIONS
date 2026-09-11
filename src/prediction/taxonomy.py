from __future__ import annotations

import re


def canonical_label(value: object) -> str:
    """Canonical form for derived learning dimensions without editing history."""
    text = str(value or "UNKNOWN").strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "_", text).strip("_")
    return text or "UNKNOWN"


def canonical_categories(values: object) -> list[str]:
    if not isinstance(values, list):
        values = [values]
    result: list[str] = []
    for value in values:
        label = canonical_label(value)
        if label not in result:
            result.append(label)
    return result or ["UNKNOWN"]
