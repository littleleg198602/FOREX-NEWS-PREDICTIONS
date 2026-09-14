from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from src.evaluation import evaluate_prediction_model2 as model2_eval
from src.learning.build_learning_profile_model2 import _news_age_bucket
from src.prediction.forecast import forecast_for_horizon
from src.prediction.normalization import normalize_prediction, validate_normalized_prediction
from src.statistics.build_stats_model2 import _coverage


def _model2_prediction() -> dict:
    return {
        "prediction_id": "p-model2",
        "event_id": "e-model2",
        "created_at_utc": "2026-09-11T08:00:00Z",
        "event_time_utc": "2026-09-11T07:55:00Z",
        "published_at_utc": "2026-09-11T07:55:00Z",
        "eligible_for_hit_rate": True,
        "backfilled": False,
        "categories": ["MACRO"],
        "model_version": "2.0.0",
        "prediction_model_version": "2.0.0",
        "methodology_version": "3.0.0",
        "evidence": {
            "article_role": "DATA_RELEASE",
            "source_quality": "PRIMARY",
            "source_verified": True,
            "news_age_minutes": 5,
            "novelty": "HIGH",
            "attention": "HIGH",
            "dominant_driver": "rates",
            "surprise": {"actual": 3.0, "consensus": 2.0, "previous": 1.0},
            "absorption": {"state": "PARTIALLY_PRICED"},
            "cross_asset_confirmation": {"verdict": "CONFIRMED", "observations": {}},
        },
        "predictions": [
            {
                "instrument": "SP500",
                "immediate": {"direction": "UP", "confidence": 6},
                "next_session": {"direction": "MIXED", "confidence": 4},
                "horizons": {
                    "15m": {"direction": "UP", "confidence": 6},
                    "1h": {"direction": "DOWN", "confidence": 5},
                    "4h": {"direction": "UP", "confidence": 4},
                    "next_session": {"direction": "MIXED", "confidence": 4},
                },
                "technical_state": {
                    "reaction_since_event_pct": 0.1,
                    "trend_5_15m": "UP",
                    "trend_1h": "FLAT",
                    "session_location": "MID_RANGE",
                    "extension_state": "NORMAL",
                    "market_open": True,
                },
                "mechanism": "test",
                "invalidation": "test",
                "counter_case": "opposite mechanism could dominate",
            }
        ],
    }


def test_explicit_horizon_forecasts_do_not_reuse_immediate_direction():
    item = _model2_prediction()["predictions"][0]
    assert forecast_for_horizon(item, "15m")["direction"] == "UP"
    assert forecast_for_horizon(item, "1h")["direction"] == "DOWN"
    assert forecast_for_horizon(item, "4h")["direction"] == "UP"
    assert forecast_for_horizon(item, "next_session")["direction"] == "MIXED"


def test_legacy_prediction_still_falls_back_to_immediate():
    item = {
        "instrument": "SP500",
        "immediate": {"direction": "DOWN", "confidence": 5},
        "next_session": {"direction": "UP", "confidence": 4},
    }
    assert forecast_for_horizon(item, "15m")["direction"] == "DOWN"
    assert forecast_for_horizon(item, "1h")["direction"] == "DOWN"
    assert forecast_for_horizon(item, "4h")["direction"] == "DOWN"
    assert forecast_for_horizon(item, "next_session")["direction"] == "UP"


def test_model2_requires_evidence_and_all_horizons():
    normalized = normalize_prediction(_model2_prediction())
    errors, _ = validate_normalized_prediction(normalized, {"SP500"})
    assert errors == []

    broken = _model2_prediction()
    del broken["evidence"]
    del broken["predictions"][0]["horizons"]["4h"]
    errors, _ = validate_normalized_prediction(normalize_prediction(broken), {"SP500"})
    assert any("requires evidence" in error for error in errors)
    assert any("horizons missing 4h" in error for error in errors)


def test_model2_evaluator_uses_different_fixed_horizon_directions(monkeypatch):
    now = datetime.now(timezone.utc)
    decision = now - timedelta(hours=5)
    index = pd.date_range(decision - timedelta(minutes=90), decision + timedelta(minutes=260), freq="1min", tz="UTC")
    close = [100.0 for _ in index]
    frame = pd.DataFrame({"open": close, "high": [100.2] * len(index), "low": [99.8] * len(index), "close": close}, index=index)
    frame.attrs["interval_minutes"] = 1

    monkeypatch.setattr(model2_eval, "fetch_1m_window", lambda *args, **kwargs: frame)
    monkeypatch.setattr(model2_eval, "load_instruments", lambda: {"SP500": {"yahoo_symbol": "^GSPC"}})
    monkeypatch.setattr(model2_eval.legacy, "_evaluate_next_session", lambda *args, **kwargs: {"status": "PENDING"})

    item = _model2_prediction()["predictions"][0]
    result = model2_eval.evaluate_one_instrument("p", decision, item)
    assert result["forecast_structure"] == "explicit_horizons"
    assert result["evaluations"]["15m"]["predicted_direction"] == "UP"
    assert result["evaluations"]["1h"]["predicted_direction"] == "DOWN"
    assert result["evaluations"]["4h"]["predicted_direction"] == "UP"


def test_directional_coverage_is_separate_from_accuracy():
    blocks = {
        "directional": {"15m": {"n": 40}},
        "mixed_neutral": {"15m": {"n": 60}},
        "volatility": {"15m": {"n": 0}},
    }
    row = _coverage(blocks)["15m"]
    assert row["directional_n"] == 40
    assert row["all_scored_n"] == 100
    assert row["coverage_pct"] == 40.0


def test_news_age_bucket_is_information_feature_not_score_tuning():
    assert _news_age_bucket(2) == "0-5m"
    assert _news_age_bucket(8) == "5-15m"
    assert _news_age_bucket(45) == "30-60m"
    assert _news_age_bucket(150) == "120m+"
