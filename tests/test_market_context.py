from src.market_data.context_snapshot import _trend_label, context_signature


def _config():
    return {
        "regimes": {
            "VIX": {"low_below": 18.0, "high_at_or_above": 25.0},
            "DXY": {"trend_threshold_pct_60m": 0.15},
            "US2Y": {"trend_threshold_abs_60m": 0.03},
            "US10Y": {"trend_threshold_abs_60m": 0.03},
            "WTI": {"trend_threshold_pct_60m": 0.75},
            "BRENT": {"trend_threshold_pct_60m": 0.75},
        }
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
