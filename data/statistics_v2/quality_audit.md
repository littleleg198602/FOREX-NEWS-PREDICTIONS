# Prediction quality audit

Generated: 2026-09-22T08:22:43.718517+00:00

## Directional accuracy

- 15m: 156/330 = 47.27%
- 1h: 122/320 = 38.12%
- 4h: 82/201 = 40.8%
- next_session: 156/294 = 53.06%

## Detection latency

- events with usable latency: 299
- mean: 61.59 min; median: 43.0 min
- >=30 min: 66.56%; >=60 min: 31.44%

## Realized direction instability

- 15m_vs_1h: class changed 42.57% of 303 comparable rows; full UP/DOWN reversal 21.45%
- 1h_vs_4h: class changed 37.5% of 192 comparable rows; full UP/DOWN reversal 17.19%
- 15m_vs_4h: class changed 42.19% of 192 comparable rows; full UP/DOWN reversal 21.35%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
