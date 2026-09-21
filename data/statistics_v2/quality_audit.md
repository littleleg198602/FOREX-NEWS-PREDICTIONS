# Prediction quality audit

Generated: 2026-09-21T20:02:00.652827+00:00

## Directional accuracy

- 15m: 152/324 = 46.91%
- 1h: 120/315 = 38.1%
- 4h: 81/195 = 41.54%
- next_session: 148/279 = 53.05%

## Detection latency

- events with usable latency: 285
- mean: 61.03 min; median: 42.0 min
- >=30 min: 65.61%; >=60 min: 30.88%

## Realized direction instability

- 15m_vs_1h: class changed 42.62% of 298 comparable rows; full UP/DOWN reversal 21.48%
- 1h_vs_4h: class changed 37.23% of 188 comparable rows; full UP/DOWN reversal 17.02%
- 15m_vs_4h: class changed 42.55% of 188 comparable rows; full UP/DOWN reversal 21.28%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
