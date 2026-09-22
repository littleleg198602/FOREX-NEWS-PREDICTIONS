# Prediction quality audit

Generated: 2026-09-22T22:16:18.151631+00:00

## Directional accuracy

- 15m: 164/358 = 45.81%
- 1h: 133/350 = 38.0%
- 4h: 88/214 = 41.12%
- next_session: 168/314 = 53.5%

## Detection latency

- events with usable latency: 317
- mean: 63.08 min; median: 45.0 min
- >=30 min: 67.82%; >=60 min: 33.44%

## Realized direction instability

- 15m_vs_1h: class changed 42.77% of 325 comparable rows; full UP/DOWN reversal 22.46%
- 1h_vs_4h: class changed 37.25% of 204 comparable rows; full UP/DOWN reversal 18.14%
- 15m_vs_4h: class changed 43.5% of 200 comparable rows; full UP/DOWN reversal 23.5%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
