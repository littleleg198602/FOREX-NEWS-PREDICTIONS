# Prediction quality audit

Generated: 2026-09-22T17:58:13.784473+00:00

## Directional accuracy

- 15m: 160/341 = 46.92%
- 1h: 129/333 = 38.74%
- 4h: 86/209 = 41.15%
- next_session: 168/314 = 53.5%

## Detection latency

- events with usable latency: 311
- mean: 63.12 min; median: 44.0 min
- >=30 min: 67.85%; >=60 min: 33.44%

## Realized direction instability

- 15m_vs_1h: class changed 42.12% of 311 comparable rows; full UP/DOWN reversal 21.54%
- 1h_vs_4h: class changed 36.0% of 200 comparable rows; full UP/DOWN reversal 16.5%
- 15m_vs_4h: class changed 42.35% of 196 comparable rows; full UP/DOWN reversal 21.94%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
