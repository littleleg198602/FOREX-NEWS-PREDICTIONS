# Prediction quality audit

Generated: 2026-09-18T07:42:20.992902+00:00

## Directional accuracy

- 15m: 123/281 = 43.77%
- 1h: 109/277 = 39.35%
- 4h: 71/175 = 40.57%
- next_session: 130/227 = 57.27%

## Detection latency

- events with usable latency: 245
- mean: 58.48 min; median: 39.0 min
- >=30 min: 63.27%; >=60 min: 27.76%

## Realized direction instability

- 15m_vs_1h: class changed 43.18% of 264 comparable rows; full UP/DOWN reversal 21.21%
- 1h_vs_4h: class changed 38.82% of 170 comparable rows; full UP/DOWN reversal 17.65%
- 15m_vs_4h: class changed 44.12% of 170 comparable rows; full UP/DOWN reversal 22.94%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
