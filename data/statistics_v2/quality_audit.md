# Prediction quality audit

Generated: 2026-09-23T22:16:25.203473+00:00

## Directional accuracy

- 15m: 172/391 = 43.99%
- 1h: 138/386 = 35.75%
- 4h: 91/240 = 37.92%
- next_session: 178/339 = 52.51%

## Detection latency

- events with usable latency: 341
- mean: 61.66 min; median: 43.05 min
- >=30 min: 66.57%; >=60 min: 32.84%

## Realized direction instability

- 15m_vs_1h: class changed 43.38% of 355 comparable rows; full UP/DOWN reversal 21.69%
- 1h_vs_4h: class changed 37.28% of 228 comparable rows; full UP/DOWN reversal 16.67%
- 15m_vs_4h: class changed 44.89% of 225 comparable rows; full UP/DOWN reversal 23.11%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
