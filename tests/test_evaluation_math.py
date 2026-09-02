from src.evaluation.evaluate_prediction import _pct_change, _actual_direction, _direction_correct


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
