# Prediction quality audit

Generated: 2026-09-22T11:34:45.061538+00:00

## Directional accuracy

- 15m: 156/332 = 46.99%
- 1h: 126/324 = 38.89%
- 4h: 82/201 = 40.8%
- next_session: 156/294 = 53.06%

## Detection latency

- events with usable latency: 301
- mean: 62.27 min; median: 43.0 min
- >=30 min: 66.78%; >=60 min: 31.89%

## Realized direction instability

- 15m_vs_1h: class changed 42.95% of 305 comparable rows; full UP/DOWN reversal 21.97%
- 1h_vs_4h: class changed 37.5% of 192 comparable rows; full UP/DOWN reversal 17.19%
- 15m_vs_4h: class changed 42.19% of 192 comparable rows; full UP/DOWN reversal 21.35%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
