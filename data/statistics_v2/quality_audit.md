# Prediction quality audit

Generated: 2026-09-17T11:28:14.335328+00:00

## Directional accuracy

- 15m: 118/269 = 43.87%
- 1h: 105/265 = 39.62%
- 4h: 70/166 = 42.17%
- next_session: 120/203 = 59.11%

## Detection latency

- events with usable latency: 233
- mean: 59.23 min; median: 38.0 min
- >=30 min: 63.09%; >=60 min: 27.47%

## Realized direction instability

- 15m_vs_1h: class changed 42.52% of 254 comparable rows; full UP/DOWN reversal 20.87%
- 1h_vs_4h: class changed 40.37% of 161 comparable rows; full UP/DOWN reversal 18.63%
- 15m_vs_4h: class changed 43.48% of 161 comparable rows; full UP/DOWN reversal 22.36%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
