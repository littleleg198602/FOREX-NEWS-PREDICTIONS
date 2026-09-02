from src.learning.build_learning_profile import _confidence_bucket, _finalize, _recommendation


def test_confidence_buckets():
    assert _confidence_bucket(3) == "1-4"
    assert _confidence_bucket(5) == "5-6"
    assert _confidence_bucket(8) == "7-8"
    assert _confidence_bucket(10) == "9-10"
    assert _confidence_bucket(None) == "UNKNOWN"


def test_small_sample_does_not_change_model():
    stats = _finalize({"n": 9, "correct": 9, "sum_change_pct": 1.0})
    assert stats["sample_status"] == "INSUFFICIENT"
    assert stats["learning_weight"] == 0.0
    assert _recommendation(stats) == "NO_CHANGE"


def test_ten_samples_are_only_early_signal():
    stats = _finalize({"n": 10, "correct": 10, "sum_change_pct": 1.0})
    assert stats["sample_status"] == "EARLY_SIGNAL"
    assert _recommendation(stats) == "WATCH_ONLY"


def test_twenty_nine_samples_are_not_actionable():
    stats = _finalize({"n": 29, "correct": 29, "sum_change_pct": 2.0})
    assert stats["sample_status"] == "EARLY_SIGNAL"
    assert _recommendation(stats) == "WATCH_ONLY"


def test_correlated_observations_from_few_events_are_not_actionable():
    stats = _finalize(
        {
            "n": 40,
            "correct": 35,
            "sum_change_pct": 5.0,
            "prediction_ids": {"event-a", "event-b", "event-c"},
        }
    )
    assert stats["unique_events"] == 3
    assert stats["sample_status"] == "INSUFFICIENT"
    assert _recommendation(stats) == "NO_CHANGE"


def test_actionable_strong_segment_can_boost_confidence():
    stats = _finalize({"n": 40, "correct": 30, "sum_change_pct": 5.0})
    assert stats["sample_status"] == "ACTIONABLE"
    assert stats["raw_hit_rate_pct"] == 75.0
    assert _recommendation(stats) == "BOOST_CONFIDENCE"


def test_actionable_weak_segment_can_be_reduced():
    stats = _finalize({"n": 40, "correct": 10, "sum_change_pct": -3.0})
    assert stats["sample_status"] == "ACTIONABLE"
    assert _recommendation(stats) == "REDUCE_OR_AVOID"
