# Prediction quality audit

Generated: 2026-09-17T01:32:59.321217+00:00

## Directional accuracy

- 15m: 116/261 = 44.44%
- 1h: 104/257 = 40.47%
- 4h: 67/162 = 41.36%
- next_session: 120/197 = 60.91%

## Detection latency

- events with usable latency: 227
- mean: 60.36 min; median: 39.28 min
- >=30 min: 64.76%; >=60 min: 28.19%

## Realized direction instability

- 15m_vs_1h: class changed 42.68% of 246 comparable rows; full UP/DOWN reversal 20.33%
- 1h_vs_4h: class changed 41.14% of 158 comparable rows; full UP/DOWN reversal 18.99%
- 15m_vs_4h: class changed 43.67% of 158 comparable rows; full UP/DOWN reversal 22.15%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
