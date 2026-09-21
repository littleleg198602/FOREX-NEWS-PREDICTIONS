# Prediction quality audit

Generated: 2026-09-21T15:38:26.018129+00:00

## Directional accuracy

- 15m: 149/319 = 46.71%
- 1h: 118/310 = 38.06%
- 4h: 79/189 = 41.8%
- next_session: 148/279 = 53.05%

## Detection latency

- events with usable latency: 281
- mean: 60.23 min; median: 41.8 min
- >=30 min: 65.12%; >=60 min: 29.89%

## Realized direction instability

- 15m_vs_1h: class changed 43.0% of 293 comparable rows; full UP/DOWN reversal 21.84%
- 1h_vs_4h: class changed 38.04% of 184 comparable rows; full UP/DOWN reversal 17.39%
- 15m_vs_4h: class changed 42.93% of 184 comparable rows; full UP/DOWN reversal 21.74%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
