# Prediction quality audit

Generated: 2026-09-24T07:28:30.340086+00:00

## Directional accuracy

- 15m: 175/395 = 44.3%
- 1h: 140/391 = 35.81%
- 4h: 92/241 = 38.17%
- next_session: 186/355 = 52.39%

## Detection latency

- events with usable latency: 349
- mean: 62.09 min; median: 44.15 min
- >=30 min: 67.34%; >=60 min: 33.81%

## Realized direction instability

- 15m_vs_1h: class changed 43.3% of 358 comparable rows; full UP/DOWN reversal 21.79%
- 1h_vs_4h: class changed 37.28% of 228 comparable rows; full UP/DOWN reversal 16.67%
- 15m_vs_4h: class changed 44.69% of 226 comparable rows; full UP/DOWN reversal 23.01%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
