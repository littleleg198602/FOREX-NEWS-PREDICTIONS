from src.evaluation.evaluate_all import _merge_evaluation, _merge_result


def test_merge_result_preserves_existing_horizon_order():
    existing = {
        "instrument": "SP500",
        "status": "PARTIAL",
        "evaluations": {
            "next_session": {"status": "DONE", "correct": True},
            "1h": {"status": "DONE", "correct": False},
            "15m": {"status": "DONE", "correct": True},
        },
    }
    new = {
        "instrument": "SP500",
        "status": "DONE",
        "evaluations": {
            "15m": {"status": "DONE", "correct": True},
            "1h": {"status": "DONE", "correct": False},
            "4h": {"status": "DONE", "correct": True},
            "next_session": {"status": "DONE", "correct": True},
        },
    }

    merged = _merge_result(existing, new)

    assert list(merged["evaluations"]) == ["next_session", "1h", "15m", "4h"]
    assert merged["evaluations"]["next_session"] == existing["evaluations"]["next_session"]
    assert merged["status"] == "DONE"


def test_retry_with_only_new_evaluated_timestamp_is_semantically_unchanged():
    existing = {
        "evaluation_version": "2.0.0",
        "prediction_id": "p1",
        "evaluated_at_utc": "2026-09-21T01:00:00+00:00",
        "market_context": {"regimes": {"DXY": "RISING"}},
        "results": [
            {
                "instrument": "XAUUSD",
                "status": "DONE",
                "evaluations": {
                    "15m": {"status": "DONE", "correct": True},
                    "1h": {"status": "DONE", "correct": True},
                    "4h": {"status": "DONE", "correct": False},
                    "next_session": {"status": "DONE", "correct": True},
                },
            }
        ],
    }
    retry = {
        **existing,
        "evaluated_at_utc": "2026-09-21T02:00:00+00:00",
    }

    merged = _merge_evaluation(existing, retry)

    assert merged == existing
