from datetime import datetime, timedelta, timezone

import pandas as pd

from src.market_data import context_snapshot as context_module
from src.market_data.context_snapshot import _candidate_snapshot, _trend_label, context_signature


def _config():
    return {
        "lookbacks_minutes": {"short": 60, "long": 240, "history": 5760},
        "freshness": {"default_max_staleness_minutes": 180},
        "regimes": {
            "VIX": {"low_below": 18.0, "high_at_or_above": 25.0},
            "DXY": {"trend_threshold_pct_60m": 0.15},
            "US2Y": {"trend_threshold_abs_60m": 0.03, "trend_threshold_pct_60m": 0.02},
            "US10Y": {"trend_threshold_abs_60m": 0.03, "trend_threshold_pct_60m": 0.02},
            "WTI": {"trend_threshold_pct_60m": 0.75},
            "BRENT": {"trend_threshold_pct_60m": 0.75},
        },
    }


def test_vix_regimes():
    cfg = _config()
    assert _trend_label("VIX", 16.0, None, None, cfg) == "LOW"
    assert _trend_label("VIX", 21.0, None, None, cfg) == "ELEVATED"
    assert _trend_label("VIX", 28.0, None, None, cfg) == "HIGH"


def test_dxy_trend_regime():
    cfg = _config()
    assert _trend_label("DXY", 100.0, 0.20, None, cfg) == "RISING"
    assert _trend_label("DXY", 100.0, -0.20, None, cfg) == "FALLING"
    assert _trend_label("DXY", 100.0, 0.05, None, cfg) == "FLAT"


def test_yield_trend_regime():
    cfg = _config()
    assert _trend_label("US10Y", 4.5, None, 0.04, cfg) == "RISING"
    assert _trend_label("US10Y", 4.5, None, -0.04, cfg) == "FALLING"
    assert _trend_label("US10Y", 4.5, None, 0.01, cfg) == "FLAT"


def test_yield_futures_proxy_is_semantically_inverted(monkeypatch):
    cfg = _config()
    decision = datetime(2026, 9, 2, 18, 0, tzinfo=timezone.utc)
    index = pd.date_range(decision - timedelta(minutes=300), periods=300, freq="1min", tz="UTC")
    closes = [100.0 + i * 0.01 for i in range(300)]
    frame = pd.DataFrame(
        {
            "open": closes,
            "high": [v + 0.01 for v in closes],
            "low": [v - 0.01 for v in closes],
            "close": closes,
        },
        index=index,
    )

    monkeypatch.setattr(context_module, "_download", lambda symbol, start, end, interval: frame)
    snapshot = _candidate_snapshot(
        "US2Y",
        {"kind": "yield", "role": "front_end_rates"},
        {
            "symbol": "ZT=F",
            "inverse_to_role": True,
            "proxy_for": "US 2Y Treasury yield",
            "trend_metric": "pct",
        },
        decision,
        cfg,
    )

    assert snapshot is not None
    assert snapshot["raw_change_pct_60m"] > 0
    assert snapshot["change_pct_60m"] < 0
    assert snapshot["regime"] == "FALLING"
    assert snapshot["inverse_to_role"] is True


def test_context_signature_is_stable():
    snapshot = {
        "regimes": {
            "VIX": "HIGH",
            "DXY": "RISING",
            "US10Y": "RISING",
            "US2Y": "FLAT",
            "WTI": "RISING",
            "BRENT": "RISING",
        }
    }
    assert context_signature(snapshot) == "DXY=RISING|US2Y=FLAT|US10Y=RISING|VIX=HIGH|WTI=RISING|BRENT=RISING"
