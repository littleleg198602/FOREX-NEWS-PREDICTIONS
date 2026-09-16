# Prediction quality audit

Generated: 2026-09-16T22:20:53.653518+00:00

## Directional accuracy

- 15m: 115/260 = 44.23%
- 1h: 103/256 = 40.23%
- 4h: 65/158 = 41.14%
- next_session: 115/188 = 61.17%

## Detection latency

- events with usable latency: 225
- mean: 60.17 min; median: 39.0 min
- >=30 min: 64.44%; >=60 min: 27.56%

## Realized direction instability

- 15m_vs_1h: class changed 42.86% of 245 comparable rows; full UP/DOWN reversal 20.41%
- 1h_vs_4h: class changed 42.21% of 154 comparable rows; full UP/DOWN reversal 19.48%
- 15m_vs_4h: class changed 42.86% of 154 comparable rows; full UP/DOWN reversal 22.08%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
