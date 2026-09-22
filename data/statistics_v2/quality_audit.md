# Prediction quality audit

Generated: 2026-09-22T07:02:45.474838+00:00

## Directional accuracy

- 15m: 156/330 = 47.27%
- 1h: 122/320 = 38.12%
- 4h: 82/199 = 41.21%
- next_session: 150/281 = 53.38%

## Detection latency

- events with usable latency: 297
- mean: 61.92 min; median: 43.0 min
- >=30 min: 67.0%; >=60 min: 31.65%

## Realized direction instability

- 15m_vs_1h: class changed 42.57% of 303 comparable rows; full UP/DOWN reversal 21.45%
- 1h_vs_4h: class changed 37.7% of 191 comparable rows; full UP/DOWN reversal 17.28%
- 15m_vs_4h: class changed 42.41% of 191 comparable rows; full UP/DOWN reversal 21.47%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
