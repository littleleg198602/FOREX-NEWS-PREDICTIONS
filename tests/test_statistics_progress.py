from src.statistics.build_stats import _combine_score_types


def test_combined_hit_rate_uses_each_score_type_correctness():
    source = {
        "directional": {
            "15m": {"n": 34, "correct": 13, "hit_rate_pct": 38.24},
            "1h": {"n": 27, "correct": 14, "hit_rate_pct": 51.85},
            "4h": {"n": 20, "correct": 9, "hit_rate_pct": 45.0},
            "next_session": {"n": 3, "correct": 2, "hit_rate_pct": 66.67},
        },
        "mixed_neutral": {
            "15m": {"n": 13, "correct": 9, "hit_rate_pct": 69.23},
            "1h": {"n": 12, "correct": 6, "hit_rate_pct": 50.0},
            "4h": {"n": 11, "correct": 9, "hit_rate_pct": 81.82},
            "next_session": {"n": 5, "correct": 2, "hit_rate_pct": 40.0},
        },
        "volatility": {
            "15m": {"n": 0, "correct": 0, "hit_rate_pct": None},
            "1h": {"n": 0, "correct": 0, "hit_rate_pct": None},
            "4h": {"n": 0, "correct": 0, "hit_rate_pct": None},
            "next_session": {"n": 0, "correct": 0, "hit_rate_pct": None},
        },
    }

    combined = _combine_score_types(source)

    assert combined["15m"]["n"] == 47
    assert combined["15m"]["correct"] == 22
    assert combined["15m"]["hit_rate_pct"] == 46.81
    assert combined["1h"]["hit_rate_pct"] == 51.28
    assert combined["4h"]["hit_rate_pct"] == 58.06
    assert combined["next_session"]["hit_rate_pct"] == 50.0
