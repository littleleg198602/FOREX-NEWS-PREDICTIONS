# Prediction quality audit

Generated: 2026-09-21T14:15:24.853243+00:00

## Directional accuracy

- 15m: 149/319 = 46.71%
- 1h: 118/310 = 38.06%
- 4h: 79/187 = 42.25%
- next_session: 148/279 = 53.05%

## Detection latency

- events with usable latency: 279
- mean: 60.02 min; median: 41.37 min
- >=30 min: 64.87%; >=60 min: 29.39%

## Realized direction instability

- 15m_vs_1h: class changed 43.0% of 293 comparable rows; full UP/DOWN reversal 21.84%
- 1h_vs_4h: class changed 37.36% of 182 comparable rows; full UP/DOWN reversal 17.58%
- 15m_vs_4h: class changed 42.31% of 182 comparable rows; full UP/DOWN reversal 21.98%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
