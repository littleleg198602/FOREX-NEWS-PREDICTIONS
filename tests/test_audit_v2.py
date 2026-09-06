from datetime import datetime, timezone

import pandas as pd

from src.evaluation.evaluate_all import _merge_evaluation
from src.learning.build_learning_profile import _add, _finalize, _new_counter
from src.market_data.context_snapshot import _last_close_before
from src.market_data.yahoo_provider import first_complete_bar_at_or_after, last_complete_bar_before
from src.prediction.normalization import normalize_market_context, normalize_prediction, validate_normalized_prediction


def _ohlc_frame(index, closes, interval_minutes=1):
    frame = pd.DataFrame(
        {
            "open": closes,
            "high": [value + 0.1 for value in closes],
            "low": [value - 0.1 for value in closes],
            "close": closes,
        },
        index=pd.DatetimeIndex(index),
    )
    frame.attrs["interval_minutes"] = interval_minutes
    return frame


def test_unfinished_one_minute_bar_is_never_reference_price():
    frame = _ohlc_frame(
        ["2026-09-06T10:14:00Z", "2026-09-06T10:15:00Z"],
        [100.0, 110.0],
        interval_minutes=1,
    )
    decision = datetime(2026, 9, 6, 10, 15, 30, tzinfo=timezone.utc)
    point = last_complete_bar_before(frame, decision)
    assert point is not None
    assert point.close == 100.0
    assert point.bar_start_utc.startswith("2026-09-06T10:14:00")
    assert point.available_at_utc.startswith("2026-09-06T10:15:00")


def test_unfinished_five_minute_context_bar_is_never_used():
    frame = _ohlc_frame(
        ["2026-09-06T10:10:00Z", "2026-09-06T10:15:00Z"],
        [100.0, 120.0],
        interval_minutes=5,
    )
    decision = datetime(2026, 9, 6, 10, 17, 0, tzinfo=timezone.utc)
    point = _last_close_before(frame, decision)
    assert point is not None
    ts, close = point
    assert close == 100.0
    assert ts == datetime(2026, 9, 6, 10, 15, tzinfo=timezone.utc)


def test_target_price_uses_first_completed_bar_not_bar_start_label():
    frame = _ohlc_frame(
        ["2026-09-06T10:15:00Z", "2026-09-06T10:16:00Z"],
        [101.0, 102.0],
        interval_minutes=1,
    )
    target = datetime(2026, 9, 6, 10, 15, 30, tzinfo=timezone.utc)
    point = first_complete_bar_at_or_after(frame, target)
    assert point is not None
    assert point.close == 101.0
    assert point.available_at_utc.startswith("2026-09-06T10:16:00")


def test_nested_source_time_and_eligibility_are_normalized_without_editing_raw_shape():
    raw = {
        "prediction_id": "p1",
        "event_id": "e1",
        "created_at_utc": "2026-09-06T10:00:00Z",
        "source": {"published_at_utc": "2026-09-06T09:55:00Z"},
        "eligibility": {"eligible_for_hit_rate": True, "backfilled": False},
        "category": "fed",
        "predictions": [
            {"instrument": "SP500", "direction": "DOWN", "confidence": 6}
        ],
        "next_session": [
            {"instrument": "SP500", "direction": "MIXED", "confidence": 4}
        ],
    }
    normalized = normalize_prediction(raw)
    assert normalized["event_time_utc"] == "2026-09-06T09:55:00Z"
    assert normalized["eligible_for_hit_rate"] is True
    assert normalized["backfilled"] is False
    assert normalized["categories"] == ["fed"]
    assert normalized["predictions"][0]["immediate"]["direction"] == "DOWN"
    assert normalized["predictions"][0]["next_session"]["direction"] == "MIXED"
    errors, warnings = validate_normalized_prediction(normalized, {"SP500"})
    assert errors == []
    assert warnings
    assert "event_time_utc" not in raw


def test_legacy_direct_market_context_becomes_canonical_regimes():
    normalized = normalize_market_context(
        {
            "DXY": {"value": 99.1, "short_term_direction": "UP", "timestamp_utc": "2026-09-06T10:00:00Z"},
            "US2Y": {"value": 4.2, "short_term_direction": "DOWN", "timestamp_utc": "2026-09-06T10:00:00Z"},
            "VIX": {"value": 14.5, "timestamp_utc": "2026-09-06T10:00:00Z"},
        }
    )
    assert normalized["regimes"]["DXY"] == "RISING"
    assert normalized["regimes"]["US2Y"] == "FALLING"
    assert normalized["regimes"]["VIX"] == "LOW"
    assert set(normalized["regimes"]) == {"DXY", "US2Y", "US10Y", "VIX", "WTI", "BRENT"}


def test_retry_provider_failure_cannot_erase_done_horizon():
    existing = {
        "evaluation_version": "2.0.0",
        "results": [
            {
                "instrument": "SP500",
                "status": "PARTIAL",
                "reference_price": 100.0,
                "evaluations": {
                    "15m": {"status": "DONE", "correct": True, "price": 101.0},
                    "1h": {"status": "PENDING"},
                },
            }
        ],
    }
    new = {
        "evaluation_version": "2.0.0",
        "results": [
            {
                "instrument": "SP500",
                "status": "PROVIDER_ERROR",
                "provider_error": "temporary outage",
                "evaluations": {},
            }
        ],
    }
    merged = _merge_evaluation(existing, new)
    result = merged["results"][0]
    assert result["reference_price"] == 100.0
    assert result["evaluations"]["15m"]["status"] == "DONE"
    assert result["evaluations"]["15m"]["price"] == 101.0


def test_learning_weights_each_event_once_even_with_many_correlated_rows():
    counter = _new_counter()
    for _ in range(10):
        _add(counter, True, 0.1, "one-big-event")
    _add(counter, False, -0.1, "second-event")
    stats = _finalize(counter)
    # Row hit rate is 10/11 = 90.9%, but event-weighted result is 50%.
    assert stats["raw_hit_rate_pct"] == 90.91
    assert stats["event_weighted_hit_rate_pct"] == 50.0
    assert stats["unique_events"] == 2
    assert stats["sample_status"] == "INSUFFICIENT"
