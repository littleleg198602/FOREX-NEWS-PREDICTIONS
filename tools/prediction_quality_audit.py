from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from src.config import ROOT
from src.prediction.normalization import normalize_prediction

HORIZONS = ("15m", "1h", "4h", "next_session")
LATENCY_BUCKETS = (
    ("0-5m", 0, 5),
    ("5-15m", 5, 15),
    ("15-30m", 15, 30),
    ("30-60m", 30, 60),
    ("60-120m", 60, 120),
    ("120m+", 120, None),
)


def _dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        out = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if out.tzinfo is None:
        out = out.replace(tzinfo=timezone.utc)
    return out.astimezone(timezone.utc)


def _latency_minutes(pred: dict) -> float | None:
    created = _dt(pred.get("created_at_utc"))
    event = _dt(pred.get("event_time_utc") or pred.get("published_at_utc"))
    if created is None or event is None:
        return None
    return max(0.0, (created - event).total_seconds() / 60.0)


def _bucket(value: float | None) -> str:
    if value is None:
        return "unknown"
    for name, lo, hi in LATENCY_BUCKETS:
        if value >= lo and (hi is None or value < hi):
            return name
    return "unknown"


def _new_counter() -> dict:
    return {"n": 0, "correct": 0, "wrong": 0, "no_move": 0, "up_actual": 0, "down_actual": 0}


def _add(counter: dict, item: dict) -> None:
    if item.get("status") != "DONE" or item.get("score_type") != "directional":
        return
    correct = item.get("correct")
    if correct is None:
        return
    counter["n"] += 1
    if bool(correct):
        counter["correct"] += 1
    else:
        counter["wrong"] += 1
    actual = item.get("actual_direction_thresholded") or item.get("actual_direction")
    if actual == "NO_MOVE":
        counter["no_move"] += 1
    elif actual == "UP":
        counter["up_actual"] += 1
    elif actual == "DOWN":
        counter["down_actual"] += 1


def _finish(counter: dict) -> dict:
    n = counter["n"]
    out = dict(counter)
    out["hit_rate_pct"] = None if not n else round(counter["correct"] / n * 100.0, 2)
    out["no_move_pct"] = None if not n else round(counter["no_move"] / n * 100.0, 2)
    return out


def _rank(mapping: dict[str, dict], min_n: int = 8, limit: int = 10) -> dict:
    rows = []
    for key, counter in mapping.items():
        done = _finish(counter)
        if done["n"] >= min_n:
            rows.append({"key": key, **done})
    rows.sort(key=lambda x: (x["hit_rate_pct"], x["n"]), reverse=True)
    return {"best": rows[:limit], "worst": list(reversed(rows[-limit:])) if rows else []}


def main() -> int:
    predictions: dict[str, dict] = {}
    for path in sorted((ROOT / "data" / "predictions").rglob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if raw.get("is_example"):
            continue
        normalized = normalize_prediction(raw)
        pid = normalized.get("prediction_id")
        if pid:
            predictions[str(pid)] = normalized

    overall = {h: _new_counter() for h in HORIZONS}
    by_latency = {h: defaultdict(_new_counter) for h in HORIZONS}
    by_instrument = {h: defaultdict(_new_counter) for h in HORIZONS}
    by_category = {h: defaultdict(_new_counter) for h in HORIZONS}
    by_confidence = {h: defaultdict(_new_counter) for h in HORIZONS}
    by_predicted_direction = {h: defaultdict(_new_counter) for h in HORIZONS}

    eligible_events: set[str] = set()
    latencies: list[float] = []
    scored_event_horizon: set[tuple[str, str]] = set()
    horizon_actuals: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)

    evaluation_files = 0
    for path in sorted((ROOT / "data" / "evaluations_v2").glob("*.json")):
        try:
            ev = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        evaluation_files += 1
        pid = str(ev.get("prediction_id") or path.stem)
        pred = predictions.get(pid)
        if not pred:
            continue
        if pred.get("backfilled") or not pred.get("eligible_for_hit_rate", True):
            continue

        eligible_events.add(pid)
        latency = _latency_minutes(pred)
        if latency is not None:
            latencies.append(latency)
        latency_bucket = _bucket(latency)
        categories = pred.get("categories") or ["UNKNOWN"]

        pred_by_instrument = {
            str(p.get("instrument")): p
            for p in pred.get("predictions", [])
            if isinstance(p, dict) and p.get("instrument")
        }

        for result in ev.get("results", []):
            if not isinstance(result, dict):
                continue
            instrument = str(result.get("instrument") or "UNKNOWN")
            pitem = pred_by_instrument.get(instrument, {})
            for horizon in HORIZONS:
                item = (result.get("evaluations") or {}).get(horizon)
                if not isinstance(item, dict) or item.get("status") != "DONE" or item.get("score_type") != "directional":
                    continue
                if item.get("correct") is None:
                    continue

                scored_event_horizon.add((pid, horizon))
                _add(overall[horizon], item)
                _add(by_latency[horizon][latency_bucket], item)
                _add(by_instrument[horizon][instrument], item)
                for category in categories:
                    _add(by_category[horizon][str(category)], item)

                if horizon == "next_session":
                    forecast = pitem.get("next_session") or {}
                else:
                    forecast = pitem.get("immediate") or {}
                confidence = forecast.get("confidence")
                direction = str(forecast.get("direction") or item.get("predicted_direction") or "UNKNOWN").upper()
                if confidence is not None:
                    try:
                        conf_key = str(int(float(confidence)))
                    except Exception:
                        conf_key = str(confidence)
                    _add(by_confidence[horizon][conf_key], item)
                _add(by_predicted_direction[horizon][direction], item)

                actual = item.get("actual_direction_thresholded") or item.get("actual_direction")
                if horizon in {"15m", "1h", "4h"} and actual in {"UP", "DOWN", "NO_MOVE"}:
                    horizon_actuals[(pid, instrument)][horizon] = actual

    flip_pairs = (("15m", "1h"), ("1h", "4h"), ("15m", "4h"))
    horizon_flip = {}
    for a, b in flip_pairs:
        eligible = 0
        opposite = 0
        any_change = 0
        for actuals in horizon_actuals.values():
            if a not in actuals or b not in actuals:
                continue
            eligible += 1
            if actuals[a] != actuals[b]:
                any_change += 1
            if {actuals[a], actuals[b]} == {"UP", "DOWN"}:
                opposite += 1
        horizon_flip[f"{a}_vs_{b}"] = {
            "n": eligible,
            "actual_class_changed": any_change,
            "actual_class_changed_pct": None if not eligible else round(any_change / eligible * 100.0, 2),
            "full_up_down_reversal": opposite,
            "full_up_down_reversal_pct": None if not eligible else round(opposite / eligible * 100.0, 2),
        }

    latency_summary = {}
    for horizon in HORIZONS:
        latency_summary[horizon] = {
            key: _finish(value)
            for key, value in sorted(by_latency[horizon].items())
        }

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Diagnostic audit of prediction information quality; no coefficient or scoring-threshold tuning.",
        "evaluation_files": evaluation_files,
        "eligible_prediction_events_seen": len(eligible_events),
        "directional_event_horizon_pairs": len(scored_event_horizon),
        "latency_minutes": {
            "n": len(latencies),
            "mean": None if not latencies else round(sum(latencies) / len(latencies), 2),
            "median": None if not latencies else round(sorted(latencies)[len(latencies)//2], 2),
            "over_30m_pct": None if not latencies else round(sum(x >= 30 for x in latencies) / len(latencies) * 100.0, 2),
            "over_60m_pct": None if not latencies else round(sum(x >= 60 for x in latencies) / len(latencies) * 100.0, 2),
        },
        "directional_overall": {h: _finish(c) for h, c in overall.items()},
        "directional_by_news_age": latency_summary,
        "directional_by_instrument_ranked": {h: _rank(m) for h, m in by_instrument.items()},
        "directional_by_category_ranked": {h: _rank(m) for h, m in by_category.items()},
        "directional_by_confidence": {
            h: {k: _finish(v) for k, v in sorted(m.items())}
            for h, m in by_confidence.items()
        },
        "directional_by_predicted_direction": {
            h: {k: _finish(v) for k, v in sorted(m.items())}
            for h, m in by_predicted_direction.items()
        },
        "actual_horizon_instability": horizon_flip,
        "structural_findings": [
            "The current prediction schema uses one 'immediate' direction for all fixed 15m, 1h and 4h horizons, although realized direction can change between those horizons.",
            "A Forex Factory article can be materially older than the prediction decision time; for such cases the target is the residual move after decision time, not the original headline reaction.",
            "Current prediction records lack a standardized surprise-vs-consensus block, first-reaction/absorption state, novelty score, source-verification state and cross-asset confirmation matrix.",
            "Directional hit rate should be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.",
        ],
    }

    out_dir = ROOT / "data" / "statistics_v2"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "quality_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = []
    md.append("# Prediction quality audit\n")
    md.append(f"Generated: {report['generated_at_utc']}\n")
    md.append("## Directional accuracy\n")
    for h in HORIZONS:
        row = report["directional_overall"][h]
        md.append(f"- {h}: {row['correct']}/{row['n']} = {row['hit_rate_pct']}%")
    md.append("\n## Detection latency\n")
    ls = report["latency_minutes"]
    md.append(f"- events with usable latency: {ls['n']}")
    md.append(f"- mean: {ls['mean']} min; median: {ls['median']} min")
    md.append(f"- >=30 min: {ls['over_30m_pct']}%; >=60 min: {ls['over_60m_pct']}%")
    md.append("\n## Realized direction instability\n")
    for key, row in horizon_flip.items():
        md.append(f"- {key}: class changed {row['actual_class_changed_pct']}% of {row['n']} comparable rows; full UP/DOWN reversal {row['full_up_down_reversal_pct']}%")
    md.append("\n## Structural findings\n")
    for item in report["structural_findings"]:
        md.append(f"- {item}")
    (out_dir / "quality_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(out_dir / "quality_audit.json")
    print(out_dir / "quality_audit.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
