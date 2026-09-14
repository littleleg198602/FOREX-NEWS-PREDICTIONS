# Prediction Model 2.0 — information before direction

## Goal

Improve genuine out-of-sample directional accuracy by improving the information set and decision process. Do not improve reported accuracy by moving scoring thresholds, changing hit-rate math, mechanically changing confidence coefficients, or replacing difficult calls with MIXED without reporting directional coverage.

## Why model 1.x is insufficient

The quality audit on 2026-09-11 found directional accuracy near 41% on 15m/1h/4h, median story-detection latency of 36.6 minutes, and realized direction changing between fixed horizons in roughly 38–41% of comparable observations. Model 1.x nevertheless reused one `immediate` direction for 15m, 1h and 4h.

Model 2.0 therefore treats the problem as **conditional residual-return forecasting from decision time**, not as a textbook mapping from a headline to an asset.

## Decision sequence

1. **Verify the event.** Prefer a primary source. Otherwise use a high-quality wire/source and record source quality and verification state.
2. **Classify the article role.** `NEW_CATALYST`, `INCREMENTAL_UPDATE`, `DATA_RELEASE`, `MARKET_RECAP`, or `COMMENTARY`. A recap of a move is not automatically a new catalyst.
3. **Measure news age.** The target starts at `created_at_utc`. If the event is old, explicitly analyze what has already happened between event time and decision time.
4. **For scheduled macro, measure surprise.** Capture actual, consensus, previous, revisions and important subcomponents. Do not reason from the headline number alone.
5. **Measure absorption.** Classify the information as `UNPRICED`, `PARTIALLY_PRICED`, `CONFIRMED_CONTINUATION`, `FADED`, `REVERSED`, `NO_REACTION`, or `UNKNOWN` from price action available before the decision.
6. **Check cross-asset confirmation.** Use the affected instrument plus the transmission assets relevant to the event: DXY, US2Y, US10Y, VIX, WTI/Brent, and relevant local FX/rates (for example JPY for NI225, GBP for UK100 and EUR for euro-area indices). Record whether the mechanism is `CONFIRMED`, `CONFLICTING`, `NEUTRAL`, or `UNKNOWN`.
7. **Check simple technical/location state.** Store reaction since event, 5–15m trend, 1h trend, session location, extension/exhaustion state and whether the relevant market is open. This is context, not indicator voting.
8. **Identify the dominant driver.** Examples: growth surprise, inflation/Fed reaction, oil-supply shock, safe-haven demand, intervention, fiscal risk, earnings/cash-flow channel.
9. **Run an adversarial counter-case.** State the strongest reason the opposite direction could occur. A directional call should survive this check.
10. **Forecast each horizon independently.** Produce 15m, 1h, 4h and next-session directions/confidences. Do not copy one `immediate` direction across all horizons.

## Event playbooks

### Scheduled macro

Use surprise versus expectations and all relevant components. Then observe the first market reaction. A strong growth release can be equity-positive through cash flows but equity-negative through higher expected rates; the state of the economy and rates decides which channel dominates.

### Central-bank communication

Separate current-policy action, reaction-function news and central-bank information about the economy. Compare with what markets already priced before the statement. Press-conference/guidance content can matter differently from the headline decision.

### Geopolitics and oil

Do not treat all conflict headlines equally. Distinguish threat/commentary, confirmed attack, infrastructure damage, shipping interruption and verified physical supply loss. A true oil-supply shock has a different transmission to equities, USD, yields and volatility than generic geopolitical rhetoric.

### FX intervention

Separate verbal intervention, rate checks, confirmed official intervention and post-intervention follow-through. The relevant FX reaction is evidence, not merely a consequence to assume.

### Politics

Require a plausible immediate policy/fiscal/energy/financial transmission channel before making strong index calls. State-level election headlines and commentary generally deserve lower directional conviction unless markets demonstrate repricing.

## Learning

Model 2.0 learns not only instrument/category outcomes but information-pattern outcomes:

- article role
- absorption state
- cross-asset confirmation
- novelty
- news-age bucket
- combinations of the above
- horizon-specific confidence

Only sufficiently large independent-event samples become ACTIONABLE. Model versions remain isolated.

## Honest performance reporting

Always show directional accuracy together with directional coverage. MIXED and VOLATILITY remain separate score types. A model that becomes more selective can be better, but the improvement must be visible as both accuracy and coverage rather than hidden by score mixing.

## Research basis

The design follows evidence from research by the Federal Reserve, NBER, ECB and IMF showing that market reactions depend on unexpected information, release details beyond headlines, investor attention, the state of the economy, cross-asset transmission, communication channels and whether geopolitical events actually impair energy supply.
