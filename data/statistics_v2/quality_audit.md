# Prediction quality audit

Generated: 2026-09-24T10:09:03.547755+00:00

## Directional accuracy

- 15m: 177/410 = 43.17%
- 1h: 148/399 = 37.09%
- 4h: 94/243 = 38.68%
- next_session: 186/355 = 52.39%

## Detection latency

- events with usable latency: 357
- mean: 61.73 min; median: 44.15 min
- >=30 min: 68.07%; >=60 min: 33.61%

## Realized direction instability

- 15m_vs_1h: class changed 44.54% of 366 comparable rows; full UP/DOWN reversal 23.5%
- 1h_vs_4h: class changed 37.39% of 230 comparable rows; full UP/DOWN reversal 16.96%
- 15m_vs_4h: class changed 44.74% of 228 comparable rows; full UP/DOWN reversal 23.25%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
