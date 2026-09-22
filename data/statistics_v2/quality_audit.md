# Prediction quality audit

Generated: 2026-09-22T04:49:32.278764+00:00

## Directional accuracy

- 15m: 156/330 = 47.27%
- 1h: 122/319 = 38.24%
- 4h: 82/198 = 41.41%
- next_session: 150/281 = 53.38%

## Detection latency

- events with usable latency: 295
- mean: 61.98 min; median: 43.0 min
- >=30 min: 66.78%; >=60 min: 31.86%

## Realized direction instability

- 15m_vs_1h: class changed 42.38% of 302 comparable rows; full UP/DOWN reversal 21.19%
- 1h_vs_4h: class changed 37.37% of 190 comparable rows; full UP/DOWN reversal 17.37%
- 15m_vs_4h: class changed 42.63% of 190 comparable rows; full UP/DOWN reversal 21.58%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
