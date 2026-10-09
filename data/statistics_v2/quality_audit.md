# Prediction quality audit

Generated: 2026-10-09T16:22:26.506770+00:00

## Directional accuracy

- 15m: 216/495 = 43.64%
- 1h: 192/490 = 39.18%
- 4h: 118/305 = 38.69%
- next_session: 259/548 = 47.26%

## Detection latency

- events with usable latency: 395
- mean: 62.6 min; median: 47.0 min
- >=30 min: 70.13%; >=60 min: 36.96%

## Realized direction instability

- 15m_vs_1h: class changed 41.29% of 448 comparable rows; full UP/DOWN reversal 20.98%
- 1h_vs_4h: class changed 39.58% of 288 comparable rows; full UP/DOWN reversal 19.1%
- 15m_vs_4h: class changed 43.86% of 285 comparable rows; full UP/DOWN reversal 24.21%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
