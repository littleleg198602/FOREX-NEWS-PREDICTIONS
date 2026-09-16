# Prediction quality audit

Generated: 2026-09-16T03:46:13.660760+00:00

## Directional accuracy

- 15m: 95/231 = 41.13%
- 1h: 94/228 = 41.23%
- 4h: 58/147 = 39.46%
- next_session: 87/153 = 56.86%

## Detection latency

- events with usable latency: 207
- mean: 53.14 min; median: 37.73 min
- >=30 min: 62.32%; >=60 min: 25.12%

## Realized direction instability

- 15m_vs_1h: class changed 38.25% of 217 comparable rows; full UP/DOWN reversal 18.89%
- 1h_vs_4h: class changed 39.86% of 143 comparable rows; full UP/DOWN reversal 17.48%
- 15m_vs_4h: class changed 42.66% of 143 comparable rows; full UP/DOWN reversal 20.28%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
