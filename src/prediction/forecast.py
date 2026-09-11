from __future__ import annotations

from typing import Any

HORIZONS = ("15m", "1h", "4h", "next_session")


def forecast_for_horizon(item: dict[str, Any], horizon: str) -> dict[str, Any]:
    """Return the forecast that existed at prediction time for one horizon.

    Prediction model 2.0 stores explicit horizon forecasts under ``horizons``.
    Historical model 1.x records fall back to ``immediate`` for 15m/1h/4h and
    ``next_session`` for the session forecast. This preserves old records while
    preventing a new 15-minute call from being silently reused as a 4-hour call.
    """
    horizons = item.get("horizons")
    if isinstance(horizons, dict):
        candidate = horizons.get(horizon)
        if isinstance(candidate, dict) and candidate.get("direction"):
            return candidate

    if horizon == "next_session":
        candidate = item.get("next_session")
    else:
        candidate = item.get("immediate")
    return candidate if isinstance(candidate, dict) else {}


def has_explicit_horizon_forecasts(item: dict[str, Any]) -> bool:
    horizons = item.get("horizons")
    return isinstance(horizons, dict) and any(
        isinstance(horizons.get(horizon), dict) and horizons[horizon].get("direction")
        for horizon in HORIZONS
    )
