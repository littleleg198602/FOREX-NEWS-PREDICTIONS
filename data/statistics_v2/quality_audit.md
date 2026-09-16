# Prediction quality audit

Generated: 2026-09-16T12:02:56.122957+00:00

## Directional accuracy

- 15m: 98/236 = 41.53%
- 1h: 98/233 = 42.06%
- 4h: 60/150 = 40.0%
- next_session: 99/168 = 58.93%

## Detection latency

- events with usable latency: 215
- mean: 56.73 min; median: 38.0 min
- >=30 min: 63.72%; >=60 min: 26.05%

## Realized direction instability

- 15m_vs_1h: class changed 38.74% of 222 comparable rows; full UP/DOWN reversal 18.92%
- 1h_vs_4h: class changed 39.04% of 146 comparable rows; full UP/DOWN reversal 17.12%
- 15m_vs_4h: class changed 42.47% of 146 comparable rows; full UP/DOWN reversal 20.55%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
