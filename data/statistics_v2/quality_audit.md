# Prediction quality audit

Generated: 2026-09-11T09:31:05.116775+00:00

## Directional accuracy

- 15m: 65/161 = 40.37%
- 1h: 62/155 = 40.0%
- 4h: 46/109 = 42.2%
- next_session: 50/104 = 48.08%

## Detection latency

- events with usable latency: 129
- mean: 48.09 min; median: 37.73 min
- >=30 min: 62.79%; >=60 min: 27.13%

## Realized direction instability

- 15m_vs_1h: class changed 37.5% of 152 comparable rows; full UP/DOWN reversal 19.08%
- 1h_vs_4h: class changed 37.14% of 105 comparable rows; full UP/DOWN reversal 14.29%
- 15m_vs_4h: class changed 40.95% of 105 comparable rows; full UP/DOWN reversal 17.14%

## Structural findings

- The current prediction schema uses one 'immediate' direction for all fixed 15m, 1h and 4h horizons, although realized direction can change between those horizons.
- A Forex Factory article can be materially older than the prediction decision time; for such cases the target is the residual move after decision time, not the original headline reaction.
- Current prediction records lack a standardized surprise-vs-consensus block, first-reaction/absorption state, novelty score, source-verification state and cross-asset confirmation matrix.
- Directional hit rate should be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
