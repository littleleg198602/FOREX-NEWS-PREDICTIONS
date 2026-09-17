# Prediction quality audit

Generated: 2026-09-17T13:32:31.560192+00:00

## Directional accuracy

- 15m: 120/271 = 44.28%
- 1h: 105/267 = 39.33%
- 4h: 70/169 = 41.42%
- next_session: 123/206 = 59.71%

## Detection latency

- events with usable latency: 233
- mean: 59.23 min; median: 38.0 min
- >=30 min: 63.09%; >=60 min: 27.47%

## Realized direction instability

- 15m_vs_1h: class changed 42.97% of 256 comparable rows; full UP/DOWN reversal 21.48%
- 1h_vs_4h: class changed 39.63% of 164 comparable rows; full UP/DOWN reversal 18.29%
- 15m_vs_4h: class changed 43.29% of 164 comparable rows; full UP/DOWN reversal 22.56%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
