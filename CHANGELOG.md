# Changelog

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
- `next_session` remains intentionally pending until exchange-calendar aware logic is implemented.

No automatic trading functionality was added.
