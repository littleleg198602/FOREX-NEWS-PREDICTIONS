# Prediction quality audit

Generated: 2026-10-06T17:20:00.825851+00:00

## Directional accuracy

- 15m: 205/475 = 43.16%
- 1h: 182/468 = 38.89%
- 4h: 107/281 = 38.08%
- next_session: 246/514 = 47.86%

## Detection latency

- events with usable latency: 391
- mean: 62.6 min; median: 46.35 min
- >=30 min: 69.82%; >=60 min: 36.32%

## Realized direction instability

- 15m_vs_1h: class changed 42.76% of 428 comparable rows; full UP/DOWN reversal 21.96%
- 1h_vs_4h: class changed 40.38% of 265 comparable rows; full UP/DOWN reversal 20.0%
- 15m_vs_4h: class changed 44.87% of 263 comparable rows; full UP/DOWN reversal 24.71%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
