# Prediction quality audit

Generated: 2026-09-18T00:25:48.288887+00:00

## Directional accuracy

- 15m: 121/279 = 43.37%
- 1h: 107/274 = 39.05%
- 4h: 70/174 = 40.23%
- next_session: 127/221 = 57.47%

## Detection latency

- events with usable latency: 239
- mean: 58.71 min; median: 38.0 min
- >=30 min: 63.18%; >=60 min: 27.62%

## Realized direction instability

- 15m_vs_1h: class changed 43.51% of 262 comparable rows; full UP/DOWN reversal 21.37%
- 1h_vs_4h: class changed 39.05% of 169 comparable rows; full UP/DOWN reversal 17.75%
- 15m_vs_4h: class changed 44.38% of 169 comparable rows; full UP/DOWN reversal 23.08%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
