# Changelog

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
