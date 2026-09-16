# Prediction quality audit

Generated: 2026-09-16T17:07:56.274534+00:00

## Directional accuracy

- 15m: 98/239 = 41.0%
- 1h: 98/236 = 41.53%
- 4h: 61/154 = 39.61%
- next_session: 115/188 = 61.17%

## Detection latency

- events with usable latency: 219
- mean: 60.61 min; median: 39.28 min
- >=30 min: 64.38%; >=60 min: 27.4%

## Realized direction instability

- 15m_vs_1h: class changed 38.22% of 225 comparable rows; full UP/DOWN reversal 18.67%
- 1h_vs_4h: class changed 40.67% of 150 comparable rows; full UP/DOWN reversal 18.67%
- 15m_vs_4h: class changed 44.0% of 150 comparable rows; full UP/DOWN reversal 22.67%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
