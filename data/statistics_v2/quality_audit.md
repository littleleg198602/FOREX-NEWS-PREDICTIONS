# Prediction quality audit

Generated: 2026-09-16T06:55:57.149948+00:00

## Directional accuracy

- 15m: 95/233 = 40.77%
- 1h: 95/229 = 41.48%
- 4h: 59/149 = 39.6%
- next_session: 87/153 = 56.86%

## Detection latency

- events with usable latency: 211
- mean: 55.81 min; median: 38.0 min
- >=30 min: 63.03%; >=60 min: 25.59%

## Realized direction instability

- 15m_vs_1h: class changed 38.53% of 218 comparable rows; full UP/DOWN reversal 18.81%
- 1h_vs_4h: class changed 39.31% of 145 comparable rows; full UP/DOWN reversal 17.24%
- 15m_vs_4h: class changed 42.07% of 145 comparable rows; full UP/DOWN reversal 20.0%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
