# Prediction quality audit

Generated: 2026-09-17T07:45:47.875151+00:00

## Directional accuracy

- 15m: 116/263 = 44.11%
- 1h: 105/259 = 40.54%
- 4h: 70/165 = 42.42%
- next_session: 120/203 = 59.11%

## Detection latency

- events with usable latency: 229
- mean: 60.04 min; median: 39.0 min
- >=30 min: 64.19%; >=60 min: 27.95%

## Realized direction instability

- 15m_vs_1h: class changed 42.74% of 248 comparable rows; full UP/DOWN reversal 20.56%
- 1h_vs_4h: class changed 40.62% of 160 comparable rows; full UP/DOWN reversal 18.75%
- 15m_vs_4h: class changed 43.75% of 160 comparable rows; full UP/DOWN reversal 22.5%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
