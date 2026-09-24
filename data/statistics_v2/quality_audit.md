# Prediction quality audit

Generated: 2026-09-24T19:18:34.703865+00:00

## Directional accuracy

- 15m: 188/435 = 43.22%
- 1h: 166/431 = 38.52%
- 4h: 101/263 = 38.4%
- next_session: 199/380 = 52.37%

## Detection latency

- events with usable latency: 369
- mean: 61.78 min; median: 45.32 min
- >=30 min: 68.56%; >=60 min: 34.69%

## Realized direction instability

- 15m_vs_1h: class changed 44.67% of 394 comparable rows; full UP/DOWN reversal 23.35%
- 1h_vs_4h: class changed 39.52% of 248 comparable rows; full UP/DOWN reversal 19.35%
- 15m_vs_4h: class changed 44.9% of 245 comparable rows; full UP/DOWN reversal 23.67%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
