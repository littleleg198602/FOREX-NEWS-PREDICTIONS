# Prediction quality audit

Generated: 2026-09-18T18:34:55.338949+00:00

## Directional accuracy

- 15m: 144/310 = 46.45%
- 1h: 115/299 = 38.46%
- 4h: 74/180 = 41.11%
- next_session: 137/248 = 55.24%

## Detection latency

- events with usable latency: 255
- mean: 57.92 min; median: 39.0 min
- >=30 min: 63.14%; >=60 min: 27.45%

## Realized direction instability

- 15m_vs_1h: class changed 43.62% of 282 comparable rows; full UP/DOWN reversal 21.63%
- 1h_vs_4h: class changed 37.71% of 175 comparable rows; full UP/DOWN reversal 17.14%
- 15m_vs_4h: class changed 44.0% of 175 comparable rows; full UP/DOWN reversal 22.86%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
