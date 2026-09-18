# Prediction quality audit

Generated: 2026-09-18T04:11:12.073641+00:00

## Directional accuracy

- 15m: 122/280 = 43.57%
- 1h: 108/275 = 39.27%
- 4h: 70/174 = 40.23%
- next_session: 127/221 = 57.47%

## Detection latency

- events with usable latency: 241
- mean: 58.81 min; median: 39.0 min
- >=30 min: 63.49%; >=60 min: 28.22%

## Realized direction instability

- 15m_vs_1h: class changed 43.35% of 263 comparable rows; full UP/DOWN reversal 21.29%
- 1h_vs_4h: class changed 39.05% of 169 comparable rows; full UP/DOWN reversal 17.75%
- 15m_vs_4h: class changed 44.38% of 169 comparable rows; full UP/DOWN reversal 23.08%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
