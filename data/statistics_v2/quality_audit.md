# Prediction quality audit

Generated: 2026-09-21T06:56:06.477102+00:00

## Directional accuracy

- 15m: 144/312 = 46.15%
- 1h: 115/303 = 37.95%
- 4h: 75/183 = 40.98%
- next_session: 141/264 = 53.41%

## Detection latency

- events with usable latency: 269
- mean: 58.96 min; median: 40.0 min
- >=30 min: 63.57%; >=60 min: 28.25%

## Realized direction instability

- 15m_vs_1h: class changed 43.36% of 286 comparable rows; full UP/DOWN reversal 21.68%
- 1h_vs_4h: class changed 37.08% of 178 comparable rows; full UP/DOWN reversal 16.85%
- 15m_vs_4h: class changed 43.26% of 178 comparable rows; full UP/DOWN reversal 22.47%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
