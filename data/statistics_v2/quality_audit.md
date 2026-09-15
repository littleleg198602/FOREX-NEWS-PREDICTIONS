# Prediction quality audit

Generated: 2026-09-15T21:26:59.214483+00:00

## Directional accuracy

- 15m: 94/227 = 41.41%
- 1h: 93/224 = 41.52%
- 4h: 57/146 = 39.04%
- next_session: 85/143 = 59.44%

## Detection latency

- events with usable latency: 199
- mean: 52.99 min; median: 37.73 min
- >=30 min: 62.81%; >=60 min: 25.13%

## Realized direction instability

- 15m_vs_1h: class changed 38.97% of 213 comparable rows; full UP/DOWN reversal 19.25%
- 1h_vs_4h: class changed 39.44% of 142 comparable rows; full UP/DOWN reversal 16.9%
- 15m_vs_4h: class changed 42.25% of 142 comparable rows; full UP/DOWN reversal 19.72%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
