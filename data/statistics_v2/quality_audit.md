# Prediction quality audit

Generated: 2026-09-18T12:13:13.224299+00:00

## Directional accuracy

- 15m: 127/285 = 44.56%
- 1h: 109/280 = 38.93%
- 4h: 71/177 = 40.11%
- next_session: 130/227 = 57.27%

## Detection latency

- events with usable latency: 247
- mean: 58.32 min; median: 39.0 min
- >=30 min: 63.56%; >=60 min: 27.53%

## Realized direction instability

- 15m_vs_1h: class changed 43.82% of 267 comparable rows; full UP/DOWN reversal 21.72%
- 1h_vs_4h: class changed 38.37% of 172 comparable rows; full UP/DOWN reversal 17.44%
- 15m_vs_4h: class changed 44.77% of 172 comparable rows; full UP/DOWN reversal 23.26%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
