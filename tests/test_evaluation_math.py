from src.evaluation.evaluate_prediction import (
    _pct_change,
    _actual_direction,
    _direction_correct,
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
