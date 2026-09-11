# Prediction quality audit

Generated: 2026-09-11T14:03:34.625064+00:00

## Directional accuracy

- 15m: 65/165 = 39.39%
- 1h: 62/159 = 38.99%
- 4h: 46/117 = 39.32%
- next_session: 50/104 = 48.08%

## Detection latency

- events with usable latency: 131
- mean: 47.83 min; median: 37.73 min
- >=30 min: 62.6%; >=60 min: 26.72%

## Realized direction instability

- 15m_vs_1h: class changed 36.54% of 156 comparable rows; full UP/DOWN reversal 18.59%
- 1h_vs_4h: class changed 34.51% of 113 comparable rows; full UP/DOWN reversal 13.27%
- 15m_vs_4h: class changed 38.94% of 113 comparable rows; full UP/DOWN reversal 15.93%

## Structural findings

- The current prediction schema uses one 'immediate' direction for all fixed 15m, 1h and 4h horizons, although realized direction can change between those horizons.
- A Forex Factory article can be materially older than the prediction decision time; for such cases the target is the residual move after decision time, not the original headline reaction.
- Current prediction records lack a standardized surprise-vs-consensus block, first-reaction/absorption state, novelty score, source-verification state and cross-asset confirmation matrix.
- Directional hit rate should be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
