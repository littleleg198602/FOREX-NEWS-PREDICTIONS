# Changelog

## 2026-09-06 — Methodology / evaluation 2.0.0 — independent-audit hardening

- Preserved all legacy `data/evaluations` v1 files and moved new leakage-safe results to `data/evaluations_v2`; v2 statistics/learning live in `data/statistics_v2`.
- Fixed unfinished-candle look-ahead: Yahoo bars are treated as START-labelled and become usable only at bar end (`available_at`). The same rule now applies to pre-prediction market context, including 5-minute fallbacks.
- Fixed closed-market horizon contamination: 15m/1h/4h no longer use the next market open when the target market is closed or when the first available bar is too delayed. Such cases are marked `MARKET_CLOSED` or `DATA_GAP` and are not scored as fixed-horizon reactions.
- Added a volatility-aware directional no-move threshold so microscopic numerical changes are not automatically classified as UP/DOWN.
- Added canonical prediction normalization and a versioned JSON Schema. Historical nested `source.published_at_utc`, nested eligibility, flat forecast items and top-level `next_session` arrays are adapted only in derived records; original predictions remain immutable.
- Added `data/statistics_v2/data_health.json` intake validation/quarantine reporting. Legacy backfills without reliable time are quarantined rather than silently treated as evaluated live signals.
- Canonicalized market context to DXY, US2Y, US10Y, VIX, WTI and BRENT `series` + `regimes`, so legacy/direct context shapes can be consumed by learning.
- Prevented transient provider failures from deleting already completed horizons. V2 evaluation merges retries into prior results, preserves terminal horizons, retries provider failures and writes JSON atomically.
- Replaced the 90-minute-silence next-session completion heuristic with conservative confirmation by observing a later local trading date. Feed silence alone can no longer mark a session complete.
- Next-session VOLATILITY/MIXED baselines now use the previous relevant local trading-session range instead of a four-hour baseline.
- Learning now isolates `score_type` and `model_version` in every segment. Directional, MIXED and VOLATILITY outcomes therefore cannot change one another's recommendations.
- Learning evidence is event-weighted: each `event_id` contributes total weight 1 within a segment, preventing many correlated instruments from one story from masquerading as independent experiments.
- Pinned the exact dependency versions used by CI and added JSON Schema validation.
- Main hourly evaluation workflow now runs audit regression tests, prediction validation and the Yahoo tracked/context smoke test before v2 evaluation.
- Added explicit `evaluation_version` and evaluation/instrument configuration hash to every v2 evaluation for reproducibility.

The prediction model itself remains version `1.1.1`; the evaluation/methodology change is `2.0.0`. Historical predictions are not rewritten. No automatic trading functionality was added.

## 2026-09-03 — Methodology 1.1.1 / Forex Factory relative-time coverage

- Forex Factory relative timestamps such as `6 min ago`, `23 min ago` and `1 hr ago` are now treated as usable source timestamps instead of missing times.
- `published_at_utc` is derived from the observation time while preserving `source_time_text`, `observed_at_utc`, time source and uncertainty metadata.
- Absolute Forex Factory timestamps remain preferred when available.
- Live first-detection predictions with a derived relative publication time can remain eligible for hit-rate because evaluation is anchored to the real prediction decision time (`created_at_utc`), never to a backdated prediction time.
- Monitoring now scans enough stories to cover the whole interval since the previous run with an overlap window, then deduplicates by URL or normalized headline/event context. This reduces missed stories caused by rounded relative timestamps and feed reordering without generating duplicate predictions.
- Prediction/model methodology version increased to `1.1.1`.

No automatic trading functionality was added.

## 2026-09-02 — Methodology 1.1 / audit hardening

- Added explicit `config/model.yaml`; new live predictions use prediction/model methodology version `1.1.0`.
- Evaluation is anchored to the actual prediction decision time (`max(event_time, created_at_utc)`) to prevent hindsight leakage when a story is discovered after publication.
- Added closed-market handling using the last traded bar before the prediction decision and the first traded bar at/after each horizon.
- Implemented `next_session` evaluation using the instrument's configured local timezone and observed trading dates.
- Added separate scoring for `MIXED` and `VOLATILITY`; degenerate/zero baselines are not falsely scored as failures.
- Added pre-prediction market context for DXY, US2Y, US10Y, VIX, WTI and Brent.
- Replaced unavailable Yahoo US2Y cash symbol with `ZT=F` as an explicitly marked inverse Treasury-futures proxy; added context-provider fallbacks and freshness metadata.
- Extended CI smoke tests to all 12 tracked instruments and all configured context series.
- Persisted `data/evaluations/*.json` and `data/statistics/*.json` in GitHub so evaluation and learning output forms an audit trail.
- Excluded example/test records and backfilled/ineligible predictions from normal hit-rate and learning.
- Added context-aware `learning_profile.json` with minimum sample-size guardrails.
- Learning now requires enough independent `event_id` clusters as well as enough observations, preventing many correlated instruments/stories from one event from creating a false statistical edge.
- Incomplete predictions are re-evaluated automatically; fully completed predictions are skipped to reduce Yahoo calls and protect the 1-minute-data window.
- Hardened the evaluation workflow with concurrency control and rebasing before bot pushes.
- Result notifications now include 15m, 1h, 4h and `next_session` horizons.

No automatic trading functionality was added.

## 2026-09-02 — MVP market-data/evaluation layer

- Added project README and Python dependencies.
- Added Yahoo Finance as the first implemented market-data provider.
- Added 1-minute OHLC window download.
- Added reference-price rule: last complete 1-minute bar before the event.
- Added evaluation for T+15m, T+1h and T+4h.
- Added percentage change, actual direction, MFE and MAE calculations.
- Kept prediction records separate from evaluation output to prevent hindsight edits.
- Added example prediction JSON.
- Added basic unit tests for evaluation math.
- `next_session` was initially pending in the MVP and is implemented in Methodology 1.1 above.

No automatic trading functionality was added.
