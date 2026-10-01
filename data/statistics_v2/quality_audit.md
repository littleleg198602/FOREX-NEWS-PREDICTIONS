# Prediction quality audit

Generated: 2026-10-01T06:01:51.000049+00:00

## Directional accuracy

- 15m: 193/453 = 42.6%
- 1h: 174/446 = 39.01%
- 4h: 103/270 = 38.15%
- next_session: 238/480 = 49.58%

## Detection latency

- events with usable latency: 381
- mean: 62.47 min; median: 46.0 min
- >=30 min: 69.03%; >=60 min: 35.7%

## Realized direction instability

- 15m_vs_1h: class changed 44.09% of 406 comparable rows; full UP/DOWN reversal 23.15%
- 1h_vs_4h: class changed 40.55% of 254 comparable rows; full UP/DOWN reversal 20.08%
- 15m_vs_4h: class changed 45.24% of 252 comparable rows; full UP/DOWN reversal 24.21%

## Structural findings

- Historical model 1.x reused one 'immediate' direction for 15m, 1h and 4h even though realized direction changes frequently; model 2.0 resolves this with explicit horizon forecasts.
- A Forex Factory article can be materially older than the prediction decision time; the target is the residual move after decision time, not the original headline reaction.
- Historical records often lack standardized surprise, absorption, novelty, source-verification and cross-asset confirmation fields; model 2.0 requires these evidence features for new predictions.
- Directional hit rate must be reported together with directional coverage so accuracy cannot be improved merely by replacing difficult calls with MIXED.
