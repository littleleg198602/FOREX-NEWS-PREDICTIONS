# Prediction quality audit

Generated: 2026-09-23T06:06:00.651362+00:00

## Directional accuracy

- 15m: 166/361 = 45.98%
- 1h: 136/353 = 38.53%
- 4h: 90/218 = 41.28%
- next_session: 172/324 = 53.09%

## Detection latency

- events with usable latency: 321
- mean: 62.66 min; median: 45.0 min
- >=30 min: 67.6%; >=60 min: 33.02%

## Realized direction instability

- 15m_vs_1h: class changed 42.81% of 327 comparable rows; full UP/DOWN reversal 22.63%
- 1h_vs_4h: class changed 36.71% of 207 comparable rows; full UP/DOWN reversal 17.87%
- 15m_vs_4h: class changed 43.63% of 204 comparable rows; full UP/DOWN reversal 23.53%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
