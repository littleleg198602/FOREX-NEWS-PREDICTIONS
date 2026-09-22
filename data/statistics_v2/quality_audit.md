# Prediction quality audit

Generated: 2026-09-22T15:26:47.304224+00:00

## Directional accuracy

- 15m: 156/334 = 46.71%
- 1h: 126/328 = 38.41%
- 4h: 86/205 = 41.95%
- next_session: 168/314 = 53.5%

## Detection latency

- events with usable latency: 307
- mean: 62.31 min; median: 43.05 min
- >=30 min: 67.43%; >=60 min: 32.57%

## Realized direction instability

- 15m_vs_1h: class changed 42.67% of 307 comparable rows; full UP/DOWN reversal 21.82%
- 1h_vs_4h: class changed 36.73% of 196 comparable rows; full UP/DOWN reversal 16.84%
- 15m_vs_4h: class changed 42.78% of 194 comparable rows; full UP/DOWN reversal 22.16%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
