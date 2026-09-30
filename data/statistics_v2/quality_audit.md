# Prediction quality audit

Generated: 2026-09-30T19:27:51.361362+00:00

## Directional accuracy

- 15m: 191/440 = 43.41%
- 1h: 170/437 = 38.9%
- 4h: 102/266 = 38.35%
- next_session: 236/477 = 49.48%

## Detection latency

- events with usable latency: 377
- mean: 62.42 min; median: 45.75 min
- >=30 min: 68.7%; >=60 min: 35.54%

## Realized direction instability

- 15m_vs_1h: class changed 44.33% of 397 comparable rows; full UP/DOWN reversal 23.17%
- 1h_vs_4h: class changed 39.6% of 250 comparable rows; full UP/DOWN reversal 19.2%
- 15m_vs_4h: class changed 45.16% of 248 comparable rows; full UP/DOWN reversal 23.79%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
