# Prediction quality audit

Generated: 2026-09-29T20:55:19.811437+00:00

## Directional accuracy

- 15m: 191/440 = 43.41%
- 1h: 170/435 = 39.08%
- 4h: 102/265 = 38.49%
- next_session: 234/471 = 49.68%

## Detection latency

- events with usable latency: 374
- mean: 62.64 min; median: 45.83 min
- >=30 min: 68.98%; >=60 min: 35.56%

## Realized direction instability

- 15m_vs_1h: class changed 44.44% of 396 comparable rows; full UP/DOWN reversal 23.23%
- 1h_vs_4h: class changed 39.6% of 250 comparable rows; full UP/DOWN reversal 19.2%
- 15m_vs_4h: class changed 44.94% of 247 comparable rows; full UP/DOWN reversal 23.48%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
