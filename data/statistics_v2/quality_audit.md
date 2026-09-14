# Prediction quality audit

Generated: 2026-09-14T09:19:18.524840+00:00

## Directional accuracy

- 15m: 70/170 = 41.18%
- 1h: 67/165 = 40.61%
- 4h: 47/119 = 39.5%
- next_session: 50/107 = 46.73%

## Detection latency

- events with usable latency: 161
- mean: 55.47 min; median: 36.87 min
- >=30 min: 62.73%; >=60 min: 26.09%

## Realized direction instability

- 15m_vs_1h: class changed 36.25% of 160 comparable rows; full UP/DOWN reversal 18.12%
- 1h_vs_4h: class changed 35.65% of 115 comparable rows; full UP/DOWN reversal 13.91%
- 15m_vs_4h: class changed 39.13% of 115 comparable rows; full UP/DOWN reversal 16.52%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
