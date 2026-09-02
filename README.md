# FOREX-NEWS-PREDICTIONS

Analytický systém pro ukládání predikcí dopadu tržních zpráv, stahování skutečných cen, následné vyhodnocení a postupné zpřesňování budoucích predikcí.

## Stav projektu

Aktuální fáze: **automatická datová, vyhodnocovací a učící vrstva**.

Primární bezplatný zdroj tržních dat je Yahoo Finance přes `yfinance`. U některých instrumentů se používají transparentně označené proxy symboly. Twelve Data zůstává připraven jako budoucí sekundární/placený provider.

## Hlavní tok

1. Nová relevantní zpráva vytvoří strukturovaný prediction JSON.
2. Původní predikce zůstává neměnná; zpětné přepisování výsledku je zakázáno.
3. Vyhodnocení je ukotveno k okamžiku, kdy predikce skutečně vznikla (`max(event_time, created_at_utc)`), aby se nepoužívala cena z doby před predikcí.
4. Systém načte mapování instrumentu z `config/instruments.yaml` a stáhne Yahoo OHLC data.
5. Referenční cena je poslední obchodovaná svíčka před rozhodovacím okamžikem; zavřený trh se řeší poslední dostupnou obchodovanou cenou.
6. Vyhodnotí T+15m, T+1h, T+4h a `next_session`.
7. Pro UP/DOWN se hodnotí směr; MIXED a VOLATILITY mají vlastní scoring. Počítají se také změna %, MFE, MAE a použité časové body.
8. Zachytí se předpredikční kontext DXY, US2Y, US10Y, VIX, WTI a Brent pouze z informací dostupných před rozhodovacím okamžikem.
9. Výsledky se ukládají do `data/evaluations/`, agregované statistiky do `data/statistics/summary.json` a učící profil do `data/statistics/learning_profile.json`.
10. Budoucí predikce mohou používat pouze dostatečně podložené segmenty z learning profilu; malé vzorky nesmějí mechanicky měnit confidence.

## Ochrany proti přeučení a hindsight bias

- Backfilled nebo časově neověřitelné predikce se nezapočítávají do běžného hit-rate.
- Testovací/example záznamy jsou ze statistik vyloučeny.
- Learning vyžaduje nejen dost pozorování, ale také dost nezávislých prediction/event záznamů, aby jeden news event s mnoha instrumenty nevytvořil falešně velký vzorek.
- `INSUFFICIENT` segmenty nemění predikci, `EARLY_SIGNAL` je pouze orientační a až `ACTIONABLE` může upravit confidence.
- Market context je omezen na informace známé před prediction decision time.

## Automatizace

GitHub Actions pravidelně:

- spouští unit testy a smoke test Yahoo dat,
- dopočítává pouze nehotové predikce,
- vytváří/aktualizuje evaluation JSON,
- přepočítává statistiky,
- sestavuje context-aware learning profile,
- zapisuje výsledky zpět do repozitáře.

## Datové poznámky

- XAUUSD a XAGUSD používají v bezplatné Yahoo vrstvě COMEX futures proxy `GC=F` a `SI=F`.
- US2Y kontext může používat futures `ZT=F` jako inverzní proxy výnosu.
- `next_session` je v MVP odvozen z reálně pozorovaných obchodních dat a lokální timezone instrumentu; plný burzovní kalendář je možný budoucí upgrade pro svátky a zkrácené seance.

## Instalace

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Rychlý test tržních dat

```bash
python -m src.market_data.smoke_test
```

## Vyhodnocení prediction souboru

```bash
python -m src.evaluation.evaluate_prediction data/predictions/example.json
```

Výsledek se uloží do `data/evaluations/`.

## Důležité

Projekt je pouze analytický. Neobsahuje a nebude obsahovat automatické obchodování ani odesílání příkazů brokerovi.

Kompletní pravidla projektu jsou v `PROJECT_RULES.md`.
