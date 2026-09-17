# Prediction quality audit

Generated: 2026-09-17T05:34:49.365387+00:00

## Directional accuracy

- 15m: 116/262 = 44.27%
- 1h: 105/258 = 40.7%
- 4h: 68/163 = 41.72%
- next_session: 120/197 = 60.91%

## Detection latency

- events with usable latency: 229
- mean: 60.04 min; median: 39.0 min
- >=30 min: 64.19%; >=60 min: 27.95%

## Realized direction instability

- 15m_vs_1h: class changed 42.91% of 247 comparable rows; full UP/DOWN reversal 20.65%
- 1h_vs_4h: class changed 40.88% of 159 comparable rows; full UP/DOWN reversal 18.87%
- 15m_vs_4h: class changed 43.4% of 159 comparable rows; full UP/DOWN reversal 22.01%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
