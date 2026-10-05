# Prediction quality audit

Generated: 2026-10-05T07:08:46.122073+00:00

## Directional accuracy

- 15m: 197/459 = 42.92%
- 1h: 178/452 = 39.38%
- 4h: 107/275 = 38.91%
- next_session: 243/504 = 48.21%

## Detection latency

- events with usable latency: 385
- mean: 62.43 min; median: 46.02 min
- >=30 min: 69.35%; >=60 min: 35.84%

## Realized direction instability

- 15m_vs_1h: class changed 43.45% of 412 comparable rows; full UP/DOWN reversal 22.82%
- 1h_vs_4h: class changed 39.77% of 259 comparable rows; full UP/DOWN reversal 19.69%
- 15m_vs_4h: class changed 44.36% of 257 comparable rows; full UP/DOWN reversal 23.74%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
