# Datový formát FOREX-NEWS-PREDICTIONS

Tento dokument definuje závazný formát predikcí a jejich vyhodnocení.

## 1. Prediction event

Každá nová relevantní zpráva vytvoří jeden immutable prediction event. Po vytvoření se původní predikce nesmí přepisovat podle známého výsledku.

Povinná pole:

```json
{
  "prediction_id": "2026-09-02T08:32:10Z_FF_000123",
  "event_id": "IRAN_US_ESCALATION_2026_09_02",
  "created_at_utc": "2026-09-02T08:32:10Z",
  "published_at_utc": "2026-09-02T08:30:00Z",
  "source": "Forex Factory",
  "source_section": "Latest Stories",
  "source_url": "https://...",
  "headline_original": "...",
  "headline_cs": "...",
  "summary_cs": "...",
  "categories": ["GEOPOLITICS"],
  "region": ["US", "MIDDLE_EAST"],
  "model_version": "1.1.1",
  "market_context_at_prediction": {},
  "predictions": []
}
```

### 1.1 Forex Factory relativní čas

Forex Factory může místo absolutního času zobrazovat například `6 min ago`, `23 min ago` nebo `1 hr ago`. Takový údaj se **nesmí považovat za chybějící čas**.

Při prvním zachycení zprávy se uloží:

```json
{
  "source_time_text": "6 min ago",
  "observed_at_utc": "2026-09-03T05:34:00Z",
  "published_at_utc": "2026-09-03T05:28:00Z",
  "time_source": "forex_factory_relative",
  "time_is_derived": true,
  "time_precision_seconds": 60,
  "time_uncertainty_seconds": 60
}
```

Pravidla:

- absolutní timestamp z Forex Factory má přednost,
- relativní čas se přepočítá proti `observed_at_utc`,
- původní text se vždy zachová v `source_time_text`,
- přesnost/nejistota musí být explicitně uložená,
- `created_at_utc` je skutečný okamžik vytvoření predikce a nikdy se nesmí zpětně posouvat k času publikace,
- live predikce zachycená při prvním monitorovacím průchodu může být `eligible_for_hit_rate=true` i s odvozeným `published_at_utc`, protože cenové vyhodnocení se kotví k rozhodovacímu času predikce,
- pokud není dostupný ani absolutní, ani použitelný relativní čas, záznam se uloží, ale podle pravidel projektu se označí jako časově neověřený/backfilled a nezapočítává se do standardního hit-rate.

Monitoring používá překryv mezi běhy a deduplikaci podle URL nebo normalizovaného titulku/eventu, aby zaokrouhlené relativní časy nezpůsobovaly vynechané zprávy ani duplicity.

## 2. Predikce instrumentu

```json
{
  "instrument": "XAUUSD",
  "immediate": {
    "direction": "UP",
    "confidence": 8
  },
  "next_session": {
    "direction": "UP",
    "confidence": 7
  },
  "mechanism": "Geopolitická eskalace zvyšuje safe-haven poptávku.",
  "invalidation": "Rychlá diplomatická deeskalace nebo prudký růst USD a reálných výnosů.",
  "reference_price": 3485.20,
  "reference_price_time_utc": "2026-09-02T08:31:00Z",
  "market_data_source": "yahoo"
}
```

Povolené hodnoty direction:

- UP
- DOWN
- MIXED
- VOLATILITY

Confidence je celé číslo 1–10.

## 3. Referenční cena

Výchozí pravidlo:

- použít close poslední kompletní 1min svíčky před **rozhodovacím časem predikce**, ne před časem publikace, pokud predikce vznikla později,
- rozhodovací čas je `max(published_at_utc/event_time_utc, created_at_utc)`,
- nikdy nepoužívat svíčku, která obsahuje informace dostupné až po vytvoření predikce,
- pokud 1min data nejsou dostupná, použít nejjemnější dostupný interval a uložit `price_resolution`,
- pokud je trh zavřený, okamžitou reakci nehodnotit jako nulový pohyb; vyhodnocení začne od první relevantní obchodované ceny po otevření.

## 4. Market context

Pokud jsou dostupná data, ukládat v čase predikce:

```json
{
  "dxy": null,
  "us2y": null,
  "us10y": null,
  "brent": null,
  "wti": null,
  "vix": null,
  "usdjpy": null,
  "market_state": "OPEN",
  "risk_regime": "RISK_OFF"
}
```

Chybějící hodnota je `null`, nikdy se nedoplňuje odhadem. Kontext nesmí obsahovat data známá až po `created_at_utc`/rozhodovacím čase.

## 5. Evaluation record

Vyhodnocení je oddělené od původní predikce.

```json
{
  "prediction_id": "2026-09-02T08:32:10Z_FF_000123",
  "instrument": "XAUUSD",
  "market_data_source": "yahoo",
  "reference_price": 3485.20,
  "reference_price_time_utc": "2026-09-02T08:31:00Z",
  "evaluations": {
    "15m": {
      "price": 3491.10,
      "change_pct": 0.169,
      "actual_direction": "UP",
      "correct": true
    },
    "1h": {
      "price": 3503.50,
      "change_pct": 0.525,
      "actual_direction": "UP",
      "correct": true
    },
    "4h": {
      "price": 3518.40,
      "change_pct": 0.953,
      "actual_direction": "UP",
      "correct": true
    },
    "next_session": {
      "price": 3508.70,
      "change_pct": 0.674,
      "actual_direction": "UP",
      "correct": true
    }
  },
  "mfe_pct": 1.21,
  "mae_pct": -0.18
}
```

## 6. Výpočet procentního pohybu

```text
change_pct = ((evaluation_price - reference_price) / reference_price) * 100
```

## 7. MFE a MAE

Pro směrové predikce se ukládá maximální příznivý a nepříznivý pohyb od referenční ceny během sledovaného okna.

- MFE = Maximum Favorable Excursion
- MAE = Maximum Adverse Excursion

Pro DOWN predikci se znaménková logika aplikuje z pohledu predikovaného směru.

## 8. MIXED a VOLATILITY

MIXED a VOLATILITY se nesmí hodnotit stejným binárním pravidlem jako UP/DOWN.

- MIXED: hodnotí se absence stabilního jednoznačného směru vůči instrument-specific thresholdům.
- VOLATILITY: hodnotí se realized range/volatility proti běžnému historickému rozsahu instrumentu.

## 9. Zdroj dat

Architektura je provider-agnostic.

Výchozí pořadí:

1. Yahoo Finance — primární zdroj pro první bezplatnou fázi.
2. Twelve Data — volitelný placený/sekundární provider, pokud bude potřeba lepší pokrytí, SLA nebo intraday data.
3. Další fallback provider lze doplnit později.

Každý cenový záznam musí obsahovat `market_data_source`.

## 10. Auditní pravidlo

Původní prediction event je immutable. Výsledky se ukládají jako samostatné evaluation records. Jakákoli změna metodiky musí zvýšit `model_version` nebo `evaluation_version`.
