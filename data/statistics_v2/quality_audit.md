# Prediction quality audit

Generated: 2026-09-11T08:00:06.110232+00:00

## Directional accuracy

- 15m: 65/157 = 41.4%
- 1h: 62/151 = 41.06%
- 4h: 45/108 = 41.67%
- next_session: 50/104 = 48.08%

## Detection latency

- events with usable latency: 127
- mean: 47.8 min; median: 36.6 min
- >=30 min: 62.2%; >=60 min: 26.77%

## Realized direction instability

- 15m_vs_1h: class changed 37.84% of 148 comparable rows; full UP/DOWN reversal 19.59%
- 1h_vs_4h: class changed 37.5% of 104 comparable rows; full UP/DOWN reversal 14.42%
- 15m_vs_4h: class changed 41.35% of 104 comparable rows; full UP/DOWN reversal 17.31%

## Structural findings

- The current prediction schema uses one 'immediate' direction for all fixed 15m, 1h and 4h horizons, although realized direction can change between those horizons.
- A Forex Factory article can be materially older than the prediction decision time; for such cases the target is the residual move after decision time, not the original headline reaction.
- Current prediction records lack a standardized surprise-vs-consensus block, first-reaction/absorption state, novelty score, source-verification state and cross-asset confirmation matrix.
- Directional hit rate should be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
