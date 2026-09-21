# Prediction quality audit

Generated: 2026-09-21T23:22:16.950667+00:00

## Directional accuracy

- 15m: 155/327 = 47.4%
- 1h: 122/317 = 38.49%
- 4h: 82/196 = 41.84%
- next_session: 148/279 = 53.05%

## Detection latency

- events with usable latency: 285
- mean: 61.03 min; median: 42.0 min
- >=30 min: 65.61%; >=60 min: 30.88%

## Realized direction instability

- 15m_vs_1h: class changed 42.33% of 300 comparable rows; full UP/DOWN reversal 21.33%
- 1h_vs_4h: class changed 37.04% of 189 comparable rows; full UP/DOWN reversal 16.93%
- 15m_vs_4h: class changed 42.33% of 189 comparable rows; full UP/DOWN reversal 21.16%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
