# FOREX-NEWS-PREDICTIONS

Analytický systém pro ukládání predikcí dopadu tržních zpráv, stahování skutečných cen, následné vyhodnocení a postupné zpřesňování budoucích predikcí.

## Stav projektu

Aktuální metodika vyhodnocení: **2.0.0 (leakage-safe v2)**.

Predikční model zůstává `1.1.1`; v2 mění hlavně důvěryhodnost měření po nezávislém auditu. Historické v1 výsledky zůstávají zachované jako auditní stopa a nemíchají se do v2 statistik.

Primární bezplatný zdroj tržních dat je Yahoo Finance přes `yfinance`. U některých instrumentů se používají transparentně označené proxy symboly. Twelve Data je zatím pouze konfigurační budoucí sekundární provider, není implementovaný jako produkční fallback.

## Hlavní tok v2

1. Nová relevantní zpráva vytvoří strukturovaný prediction JSON.
2. Původní predikce zůstává neměnná. Starší formáty se pouze normalizují do odvozeného záznamu; raw prediction se zpětně nepřepisuje.
3. Vstup prochází verzovaným JSON Schema a validačním/data-health krokem.
4. Rozhodovací okamžik je `max(event_time, created_at_utc)`, takže systém nikdy nezačne měřit před vznikem predikce.
5. Yahoo intradenní svíčky jsou považované za START-labelled. OHLC close/high/low se smějí použít až po dokončení svíčky (`available_at`). Nedokončená svíčka tedy nesmí přinést budoucí informaci.
6. Referenční cena je poslední svíčka, jejíž close byla skutečně dostupná nejpozději v decision time.
7. Pevné horizonty T+15m, T+1h a T+4h se hodnotí jen tehdy, když trh v okolí cíle skutečně obchodoval. Další otevření trhu se nikdy nevydává za běžný 15m/1h/4h výsledek. Zavřený trh je `MARKET_CLOSED`, nepřijatelná mezera `DATA_GAP`.
8. `next_session` je samostatná úloha. Seance se nepovažuje za skončenou jen kvůli 90 minutám ticha; dokončení se konzervativně potvrzuje až pozorováním pozdějšího obchodního data.
9. UP/DOWN používají konfigurovaný práh `NO_MOVE`, aby zanedbatelný numerický pohyb nebyl automaticky UP/DOWN. MIXED a VOLATILITY mají oddělený scoring a nikdy se nevydávají za směrovou přesnost.
10. Předpredikční kontext se normalizuje do kanonických DXY, US2Y, US10Y, VIX, WTI a BRENT `series` + `regimes`. Rekonstrukce z Yahoo používá jen dokončené svíčky dostupné v decision time.
11. V2 výsledky se ukládají do `data/evaluations_v2/`, statistiky do `data/statistics_v2/summary.json`, data-health do `data/statistics_v2/data_health.json` a learning do `data/statistics_v2/learning_profile.json`.
12. Staré v1 výsledky zůstávají v `data/evaluations/` a `data/statistics/` pouze jako archivní auditní stopa.

## Ochrany proti přeučení a hindsight bias

- Backfilled, example a ineligible predikce se nezapočítávají do normálního hit-rate a learningu.
- Learning odděluje `directional`, `mixed_neutral` a `volatility`; jeden typ výsledku nemůže zlepšit doporučení jinému typu.
- Learning odděluje jednotlivé `model_version`.
- Jeden `event_id` má v segmentu celkovou váhu 1, i když stejná událost zasáhne mnoho korelovaných instrumentů.
- `INSUFFICIENT` segmenty nemění predikci, `EARLY_SIGNAL` je jen orientační a pouze `ACTIONABLE` může materiálně upravit confidence.
- Market context a referenční ceny smějí používat pouze data dostupná do prediction decision time.
- Už jednou dokončený horizont se při pozdějším výpadku providera nesmí ztratit; v2 výsledky se slučují a zapisují atomicky.
- Každý v2 evaluation ukládá `evaluation_version` a hash použité konfigurace.

## Statistiky

Primární metrika je `directional_primary` pro skutečné UP/DOWN predikce. `MIXED` a `VOLATILITY` se reportují odděleně.

`overall_combined_diagnostic` existuje pouze jako diagnostický přehled a **nesmí se interpretovat jako směrová přesnost**.

Po zavedení metodiky 2.0.0 začíná nový V2 baseline. Staré procentní výsledky v1 nejsou metodicky srovnatelné s v2 a nesmějí se používat jako přímá baseline pro tvrzení o zlepšení.

## Automatizace

Hlavní GitHub Actions workflow pravidelně:

- instaluje připnuté/ověřené verze závislostí,
- spouští unit testy a regresní testy nálezů z auditu,
- validuje a normalizuje prediction intake,
- spouští Yahoo smoke test všech sledovaných instrumentů a context řad,
- dopočítává v2 evaluations,
- přepočítává v2 statistiky,
- sestavuje v2 context-aware learning profile,
- zapisuje v2 výsledky zpět do repozitáře.

## Datové poznámky

- XAUUSD a XAGUSD používají v bezplatné Yahoo vrstvě COMEX futures proxy `GC=F` a `SI=F`.
- US2Y kontext může používat futures `ZT=F` jako explicitně označenou inverzní proxy výnosu.
- `next_session` v2 používá reálně pozorovaná obchodní data a timezone instrumentu. Konzervativní potvrzení pozdějším obchodním datem řeší falešné ukončení při výpadku feedu, ale plný burzovní kalendář pro všechny svátky/zkrácené seance je stále budoucí upgrade.
- Stabilní raw OHLC archiv a skutečný Twelve Data fallback jsou stále budoucí provozní rozšíření.

## Instalace

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Kontroly

```bash
python -m pytest tests -v
python -m src.prediction.validate_all
python -m src.market_data.smoke_test
python -m src.evaluation.evaluate_all
python -m src.statistics.build_stats
python -m src.learning.build_learning_profile
```

Jednotlivý prediction soubor lze vyhodnotit příkazem:

```bash
python -m src.evaluation.evaluate_prediction data/predictions/example.json
```

V2 výstup se ukládá do `data/evaluations_v2/`.

## Důležité

Projekt je pouze analytický. Neobsahuje a nebude obsahovat automatické obchodování ani odesílání příkazů brokerovi.

Kompletní pravidla projektu jsou v `PROJECT_RULES.md` a změny metodiky v `CHANGELOG.md`.
