# Prediction quality audit

Generated: 2026-09-21T16:54:00.226119+00:00

## Directional accuracy

- 15m: 150/322 = 46.58%
- 1h: 118/313 = 37.7%
- 4h: 81/191 = 42.41%
- next_session: 148/279 = 53.05%

## Detection latency

- events with usable latency: 283
- mean: 60.8 min; median: 42.0 min
- >=30 min: 65.37%; >=60 min: 30.39%

## Realized direction instability

- 15m_vs_1h: class changed 42.91% of 296 comparable rows; full UP/DOWN reversal 21.62%
- 1h_vs_4h: class changed 37.84% of 185 comparable rows; full UP/DOWN reversal 17.3%
- 15m_vs_4h: class changed 42.7% of 185 comparable rows; full UP/DOWN reversal 21.62%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
