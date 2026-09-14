# Prediction quality audit

Generated: 2026-09-14T04:24:48.362529+00:00

## Directional accuracy

- 15m: 66/166 = 39.76%
- 1h: 63/160 = 39.38%
- 4h: 46/118 = 38.98%
- next_session: 50/107 = 46.73%

## Detection latency

- events with usable latency: 153
- mean: 56.58 min; median: 38.0 min
- >=30 min: 62.09%; >=60 min: 27.45%

## Realized direction instability

- 15m_vs_1h: class changed 36.31% of 157 comparable rows; full UP/DOWN reversal 18.47%
- 1h_vs_4h: class changed 35.09% of 114 comparable rows; full UP/DOWN reversal 14.04%
- 15m_vs_4h: class changed 39.47% of 114 comparable rows; full UP/DOWN reversal 16.67%

## Structural findings

- The current prediction schema uses one 'immediate' direction for all fixed 15m, 1h and 4h horizons, although realized direction can change between those horizons.
- A Forex Factory article can be materially older than the prediction decision time; for such cases the target is the residual move after decision time, not the original headline reaction.
- Current prediction records lack a standardized surprise-vs-consensus block, first-reaction/absorption state, novelty score, source-verification state and cross-asset confirmation matrix.
- Directional hit rate should be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
