# Prediction quality audit

Generated: 2026-09-14T01:10:13.785852+00:00

## Directional accuracy

- 15m: 66/166 = 39.76%
- 1h: 63/160 = 39.38%
- 4h: 46/117 = 39.32%
- next_session: 50/107 = 46.73%

## Detection latency

- events with usable latency: 152
- mean: 56.69 min; median: 38.0 min
- >=30 min: 61.84%; >=60 min: 27.63%

## Realized direction instability

- 15m_vs_1h: class changed 36.31% of 157 comparable rows; full UP/DOWN reversal 18.47%
- 1h_vs_4h: class changed 34.51% of 113 comparable rows; full UP/DOWN reversal 13.27%
- 15m_vs_4h: class changed 38.94% of 113 comparable rows; full UP/DOWN reversal 15.93%

## Structural findings

- The current prediction schema uses one 'immediate' direction for all fixed 15m, 1h and 4h horizons, although realized direction can change between those horizons.
- A Forex Factory article can be materially older than the prediction decision time; for such cases the target is the residual move after decision time, not the original headline reaction.
- Current prediction records lack a standardized surprise-vs-consensus block, first-reaction/absorption state, novelty score, source-verification state and cross-asset confirmation matrix.
- Directional hit rate should be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
