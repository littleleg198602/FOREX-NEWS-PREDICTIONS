# Prediction quality audit

Generated: 2026-09-24T15:15:41.395609+00:00

## Directional accuracy

- 15m: 185/424 = 43.63%
- 1h: 154/415 = 37.11%
- 4h: 99/255 = 38.82%
- next_session: 199/380 = 52.37%

## Detection latency

- events with usable latency: 367
- mean: 61.75 min; median: 45.32 min
- >=30 min: 68.39%; >=60 min: 34.33%

## Realized direction instability

- 15m_vs_1h: class changed 44.09% of 381 comparable rows; full UP/DOWN reversal 22.57%
- 1h_vs_4h: class changed 38.75% of 240 comparable rows; full UP/DOWN reversal 18.75%
- 15m_vs_4h: class changed 44.3% of 237 comparable rows; full UP/DOWN reversal 22.36%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
