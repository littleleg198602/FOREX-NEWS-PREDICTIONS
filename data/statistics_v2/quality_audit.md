# Prediction quality audit

Generated: 2026-10-07T14:22:00.748654+00:00

## Directional accuracy

- 15m: 214/485 = 44.12%
- 1h: 192/480 = 40.0%
- 4h: 118/296 = 39.86%
- next_session: 246/530 = 46.42%

## Detection latency

- events with usable latency: 395
- mean: 62.6 min; median: 47.0 min
- >=30 min: 70.13%; >=60 min: 36.96%

## Realized direction instability

- 15m_vs_1h: class changed 41.78% of 438 comparable rows; full UP/DOWN reversal 21.46%
- 1h_vs_4h: class changed 39.07% of 279 comparable rows; full UP/DOWN reversal 19.71%
- 15m_vs_4h: class changed 43.48% of 276 comparable rows; full UP/DOWN reversal 24.28%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
