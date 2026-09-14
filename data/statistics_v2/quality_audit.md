# Prediction quality audit

Generated: 2026-09-14T14:03:57.773453+00:00

## Directional accuracy

- 15m: 77/192 = 40.1%
- 1h: 70/186 = 37.63%
- 4h: 51/129 = 39.53%
- next_session: 50/107 = 46.73%

## Detection latency

- events with usable latency: 169
- mean: 54.88 min; median: 36.87 min
- >=30 min: 62.13%; >=60 min: 26.04%

## Realized direction instability

- 15m_vs_1h: class changed 36.46% of 181 comparable rows; full UP/DOWN reversal 17.68%
- 1h_vs_4h: class changed 36.0% of 125 comparable rows; full UP/DOWN reversal 15.2%
- 15m_vs_4h: class changed 39.2% of 125 comparable rows; full UP/DOWN reversal 16.8%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
