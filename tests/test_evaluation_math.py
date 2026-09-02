from datetime import datetime, timezone

import pandas as pd

from src.evaluation.evaluate_prediction import (
    _pct_change,
    _actual_direction,
    _decision_time,
    _direction_correct,
    _next_session_frame,
    _score_non_directional,
)


def test_pct_change_up():
    assert round(_pct_change(100.0, 101.0), 6) == 1.0


def test_pct_change_down():
    assert round(_pct_change(100.0, 99.0), 6) == -1.0


def test_actual_direction():
    assert _actual_direction(0.5) == "UP"
    assert _actual_direction(-0.5) == "DOWN"
    assert _actual_direction(0.0) == "FLAT"


def test_direction_correct():
    assert _direction_correct("UP", "UP") is True
    assert _direction_correct("DOWN", "UP") is False
    assert _direction_correct("MIXED", "UP") is None
    assert _direction_correct("VOLATILITY", "DOWN") is None


def test_volatility_scoring():
    scored = _score_non_directional("VOLATILITY", 0.1, 1.5, 1.0)
    assert scored["score_type"] == "volatility"
    assert scored["correct"] is True
    assert scored["volatility_ratio"] == 1.5


def test_volatility_scoring_fails_below_threshold():
    scored = _score_non_directional("VOLATILITY", 0.1, 1.1, 1.0)
    assert scored["correct"] is False


def test_mixed_scoring_inside_neutral_envelope():
    scored = _score_non_directional("MIXED", 0.3, 1.0, 0.5)
    assert scored["score_type"] == "mixed_neutral"
    assert scored["correct"] is True


def test_mixed_scoring_outside_neutral_envelope():
    scored = _score_non_directional("MIXED", 0.8, 1.0, 0.5)
    assert scored["correct"] is False


def test_mixed_zero_baseline_is_unscored_not_false():
    scored = _score_non_directional("MIXED", 0.1, 0.2, 0.0)
    assert scored["score_type"] == "mixed_neutral"
    assert scored["correct"] is None
    assert scored["neutral_envelope_pct"] is None


def test_evaluation_anchor_never_precedes_prediction_creation():
    event = datetime(2026, 9, 2, 13, 0, tzinfo=timezone.utc)
    anchor, created, latency = _decision_time(event, "2026-09-02T13:15:00Z")
    assert anchor == datetime(2026, 9, 2, 13, 15, tzinfo=timezone.utc)
    assert created == anchor
    assert latency == 900.0


def test_pre_open_prediction_uses_same_day_as_next_relevant_session():
    decision = datetime(2026, 9, 2, 13, 0, tzinfo=timezone.utc)  # 09:00 New York
    now = datetime(2026, 9, 2, 22, 0, tzinfo=timezone.utc)
    index = pd.DatetimeIndex([
        "2026-09-01T20:00:00Z",
        "2026-09-02T13:30:00Z",
        "2026-09-02T20:00:00Z",
    ])
    frame = pd.DataFrame({"close": [100.0, 101.0, 102.0]}, index=index)
    status, session, session_date = _next_session_frame(frame, "NDX", decision, now)
    assert status == "DONE"
    assert session_date.isoformat() == "2026-09-02"
    assert session is not None and len(session) == 2


def test_intraday_prediction_waits_for_next_trading_date():
    decision = datetime(2026, 9, 2, 15, 0, tzinfo=timezone.utc)
    now = datetime(2026, 9, 3, 22, 0, tzinfo=timezone.utc)
    index = pd.DatetimeIndex([
        "2026-09-02T13:30:00Z",
        "2026-09-02T20:00:00Z",
        "2026-09-03T13:30:00Z",
        "2026-09-03T20:00:00Z",
    ])
    frame = pd.DataFrame({"close": [100.0, 101.0, 102.0, 103.0]}, index=index)
    status, session, session_date = _next_session_frame(frame, "NDX", decision, now)
    assert status == "DONE"
    assert session_date.isoformat() == "2026-09-03"
    assert session is not None and len(session) == 2
