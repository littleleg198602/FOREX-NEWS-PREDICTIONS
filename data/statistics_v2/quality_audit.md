# Prediction quality audit

Generated: 2026-09-14T11:52:59.197326+00:00

## Directional accuracy

- 15m: 73/188 = 38.83%
- 1h: 68/184 = 36.96%
- 4h: 49/121 = 40.5%
- next_session: 50/107 = 46.73%

## Detection latency

- events with usable latency: 167
- mean: 54.66 min; median: 36.6 min
- >=30 min: 61.68%; >=60 min: 25.15%

## Realized direction instability

- 15m_vs_1h: class changed 36.87% of 179 comparable rows; full UP/DOWN reversal 17.88%
- 1h_vs_4h: class changed 35.04% of 117 comparable rows; full UP/DOWN reversal 13.68%
- 15m_vs_4h: class changed 38.46% of 117 comparable rows; full UP/DOWN reversal 16.24%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
