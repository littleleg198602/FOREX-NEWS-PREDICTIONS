# Prediction quality audit

Generated: 2026-09-24T04:58:17.125323+00:00

## Directional accuracy

- 15m: 174/393 = 44.27%
- 1h: 138/387 = 35.66%
- 4h: 91/240 = 37.92%
- next_session: 185/351 = 52.71%

## Detection latency

- events with usable latency: 345
- mean: 62.19 min; median: 44.15 min
- >=30 min: 66.96%; >=60 min: 33.62%

## Realized direction instability

- 15m_vs_1h: class changed 43.54% of 356 comparable rows; full UP/DOWN reversal 21.91%
- 1h_vs_4h: class changed 37.28% of 228 comparable rows; full UP/DOWN reversal 16.67%
- 15m_vs_4h: class changed 44.89% of 225 comparable rows; full UP/DOWN reversal 23.11%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
