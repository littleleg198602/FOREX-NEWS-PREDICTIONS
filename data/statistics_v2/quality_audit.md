# Prediction quality audit

Generated: 2026-09-14T05:39:13.918526+00:00

## Directional accuracy

- 15m: 67/167 = 40.12%
- 1h: 63/161 = 39.13%
- 4h: 46/118 = 38.98%
- next_session: 50/107 = 46.73%

## Detection latency

- events with usable latency: 153
- mean: 56.58 min; median: 38.0 min
- >=30 min: 62.09%; >=60 min: 27.45%

## Realized direction instability

- 15m_vs_1h: class changed 36.71% of 158 comparable rows; full UP/DOWN reversal 18.35%
- 1h_vs_4h: class changed 35.09% of 114 comparable rows; full UP/DOWN reversal 14.04%
- 15m_vs_4h: class changed 39.47% of 114 comparable rows; full UP/DOWN reversal 16.67%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
