# Prediction quality audit

Generated: 2026-09-15T09:36:23.594021+00:00

## Directional accuracy

- 15m: 89/215 = 41.4%
- 1h: 87/210 = 41.43%
- 4h: 57/141 = 40.43%
- next_session: 67/125 = 53.6%

## Detection latency

- events with usable latency: 189
- mean: 54.61 min; median: 39.0 min
- >=30 min: 64.02%; >=60 min: 26.46%

## Realized direction instability

- 15m_vs_1h: class changed 38.12% of 202 comparable rows; full UP/DOWN reversal 19.31%
- 1h_vs_4h: class changed 39.42% of 137 comparable rows; full UP/DOWN reversal 17.52%
- 15m_vs_4h: class changed 42.34% of 137 comparable rows; full UP/DOWN reversal 18.98%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
