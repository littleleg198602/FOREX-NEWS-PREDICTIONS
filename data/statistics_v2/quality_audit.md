# Prediction quality audit

Generated: 2026-09-20T12:29:52.568327+00:00

## Directional accuracy

- 15m: 144/310 = 46.45%
- 1h: 115/302 = 38.08%
- 4h: 75/183 = 40.98%
- next_session: 137/248 = 55.24%

## Detection latency

- events with usable latency: 257
- mean: 58.31 min; median: 39.0 min
- >=30 min: 63.42%; >=60 min: 28.02%

## Realized direction instability

- 15m_vs_1h: class changed 43.51% of 285 comparable rows; full UP/DOWN reversal 21.75%
- 1h_vs_4h: class changed 37.08% of 178 comparable rows; full UP/DOWN reversal 16.85%
- 15m_vs_4h: class changed 43.26% of 178 comparable rows; full UP/DOWN reversal 22.47%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
