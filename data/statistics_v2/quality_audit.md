# Prediction quality audit

Generated: 2026-09-16T23:01:16.250673+00:00

## Directional accuracy

- 15m: 116/261 = 44.44%
- 1h: 103/256 = 40.23%
- 4h: 67/160 = 41.88%
- next_session: 115/188 = 61.17%

## Detection latency

- events with usable latency: 225
- mean: 60.17 min; median: 39.0 min
- >=30 min: 64.44%; >=60 min: 27.56%

## Realized direction instability

- 15m_vs_1h: class changed 42.86% of 245 comparable rows; full UP/DOWN reversal 20.41%
- 1h_vs_4h: class changed 41.67% of 156 comparable rows; full UP/DOWN reversal 19.23%
- 15m_vs_4h: class changed 42.95% of 156 comparable rows; full UP/DOWN reversal 22.44%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
