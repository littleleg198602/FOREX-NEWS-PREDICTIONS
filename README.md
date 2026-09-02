# FOREX-NEWS-PREDICTIONS

Analytický systém pro ukládání predikcí dopadu tržních zpráv, stahování skutečných cen a následné statistické vyhodnocování.

## Stav projektu

Aktuální fáze: **MVP datové a vyhodnocovací vrstvy**.

První verze používá Yahoo Finance přes `yfinance` jako bezplatný primární zdroj tržních dat. Twelve Data je připraven jako budoucí fallback, ale v MVP není potřeba placený účet.

## Hlavní tok

1. Vznikne strukturovaný prediction JSON.
2. Systém načte mapování instrumentu z `config/instruments.yaml`.
3. Z Yahoo stáhne 1min OHLC data okolo času zprávy.
4. Referenční cena = close poslední kompletní 1min svíčky před zprávou.
5. Vyhodnotí T+15m, T+1h a T+4h.
6. Spočítá změnu %, MFE a MAE.
7. Výsledek uloží odděleně od původní predikce.

`next_session` bude doplněn v další fázi pomocí obchodních kalendářů jednotlivých burz.

## Instalace

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Rychlý test tržních dat

```bash
python -m src.market_data.yahoo_provider XAUUSD
```

## Vyhodnocení prediction souboru

```bash
python -m src.evaluation.evaluate_prediction data/predictions/example.json
```

Výsledek se uloží do `data/evaluations/`.

## Důležité

Projekt je pouze analytický. Neobsahuje a nebude obsahovat automatické obchodování ani odesílání příkazů brokerovi.

Kompletní pravidla projektu jsou v `PROJECT_RULES.md`.
