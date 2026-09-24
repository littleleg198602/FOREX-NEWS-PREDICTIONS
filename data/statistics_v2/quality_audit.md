# Prediction quality audit

Generated: 2026-09-24T17:35:50.666904+00:00

## Directional accuracy

- 15m: 188/427 = 44.03%
- 1h: 160/421 = 38.0%
- 4h: 100/257 = 38.91%
- next_session: 199/380 = 52.37%

## Detection latency

- events with usable latency: 369
- mean: 61.78 min; median: 45.32 min
- >=30 min: 68.56%; >=60 min: 34.69%

## Realized direction instability

- 15m_vs_1h: class changed 43.52% of 386 comparable rows; full UP/DOWN reversal 22.28%
- 1h_vs_4h: class changed 39.26% of 242 comparable rows; full UP/DOWN reversal 18.6%
- 15m_vs_4h: class changed 44.77% of 239 comparable rows; full UP/DOWN reversal 23.01%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
