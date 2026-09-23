# Prediction quality audit

Generated: 2026-09-23T17:16:38.350493+00:00

## Directional accuracy

- 15m: 172/389 = 44.22%
- 1h: 138/384 = 35.94%
- 4h: 90/227 = 39.65%
- next_session: 178/339 = 52.51%

## Detection latency

- events with usable latency: 337
- mean: 62.35 min; median: 44.15 min
- >=30 min: 67.36%; >=60 min: 33.23%

## Realized direction instability

- 15m_vs_1h: class changed 43.63% of 353 comparable rows; full UP/DOWN reversal 21.81%
- 1h_vs_4h: class changed 36.28% of 215 comparable rows; full UP/DOWN reversal 17.67%
- 15m_vs_4h: class changed 44.34% of 212 comparable rows; full UP/DOWN reversal 24.06%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
