# Prediction quality audit

Generated: 2026-09-24T13:45:15.860170+00:00

## Directional accuracy

- 15m: 179/414 = 43.24%
- 1h: 152/409 = 37.16%
- 4h: 99/255 = 38.82%
- next_session: 199/380 = 52.37%

## Detection latency

- events with usable latency: 363
- mean: 61.5 min; median: 44.15 min
- >=30 min: 68.04%; >=60 min: 33.61%

## Realized direction instability

- 15m_vs_1h: class changed 44.8% of 375 comparable rows; full UP/DOWN reversal 22.93%
- 1h_vs_4h: class changed 38.75% of 240 comparable rows; full UP/DOWN reversal 18.75%
- 15m_vs_4h: class changed 44.3% of 237 comparable rows; full UP/DOWN reversal 22.36%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
