# FOREX-NEWS-PREDICTIONS — pravidla, účel a struktura projektu

## 1. Účel projektu

FOREX-NEWS-PREDICTIONS je analytický projekt pro sledování tržně významných zpráv, vytváření krátkodobých predikcí směru vybraných instrumentů a následné statistické vyhodnocování přesnosti těchto predikcí.

Projekt má čtyři hlavní cíle:

1. Zachytit nové relevantní zprávy z Forex Factory, zejména sekce Hot Story a Latest Stories.
2. U každé významné zprávy vytvořit strukturovanou predikci dopadu na sledované instrumenty.
3. Po zveřejnění predikce zaznamenat skutečný vývoj cen v definovaných časových horizontech.
4. Z historie výsledků postupně zpřesňovat budoucí predikce a určovat, pro které typy zpráv a instrumentů mají predikce skutečnou statistickou hodnotu.

Projekt je pouze analytický a informační. Nesmí obsahovat automatické zadávání obchodů, správu pozic, automatické připojení k brokerovi za účelem exekuce obchodů ani jinou formu automatického obchodování.

---

## 2. Sledované instrumenty

Primární sledovaný seznam:

- XAUUSD — zlato
- XAGUSD — stříbro
- NI225 — Nikkei 225
- AUS200 — Australia 200
- GDAXI — DAX
- FCHI40 — CAC 40
- STOXX50 — Euro Stoxx 50
- UK100 — FTSE 100
- SPA35 — IBEX 35
- NDX — Nasdaq 100
- WS30 — Dow Jones 30
- SP500 — S&P 500

Pokud bude později seznam rozšířen, musí být změna provedena centrálně v konfiguraci a zdokumentována.

---

## 3. Zdroje zpráv

### Primární zdroj

Forex Factory News:

- Hot Story
- Latest Stories

### Pravidla práce se zprávami

Do systému se ukládají pouze nové a tržně relevantní zprávy.

Ignorovat:

- reklamy,
- duplicity,
- opakované články bez nové informace,
- nízkohodnotné komentáře z fór,
- zprávy bez rozumného přenosového mechanismu na sledované instrumenty,
- čisté názory bez nové informace, pokud samy o sobě nemění tržní očekávání.

Pokud už byla událost analyzována, nový článek se považuje za nový signál pouze tehdy, když přináší skutečně nový vývoj, který může změnit interpretaci trhu.

Každá zpráva má mít pokud možno uložen:

- přesný čas zachycení,
- čas publikace,
- zdroj,
- URL,
- originální titulek,
- český překlad titulku,
- krátké české shrnutí,
- kategorii zprávy,
- zemi/region,
- hlavní ekonomické nebo geopolitické téma.

---

## 4. Kategorie zpráv

Každá zpráva má být zařazena minimálně do jedné kategorie. Doporučené kategorie:

- CENTRAL_BANK
- INTEREST_RATES
- INFLATION
- LABOR_MARKET
- GDP_GROWTH
- PMI_ACTIVITY
- RETAIL_CONSUMPTION
- FX_INTERVENTION
- BOND_YIELDS
- ENERGY_OIL
- GEOPOLITICS
- WAR_CONFLICT
- TRADE_TARIFFS
- FISCAL_POLICY
- CORPORATE_MACRO
- COMMODITIES
- OTHER_MACRO

Je možné použít více tagů současně.

---

## 5. Povinná struktura každé predikce

Každá relevantní zpráva musí mít:

### 5.1 Překlad titulku

Přirozený český překlad, ne doslovný strojový překlad.

### 5.2 Shrnutí

Krátké vysvětlení toho, co se skutečně změnilo a proč je informace tržně relevantní.

### 5.3 Dotčené instrumenty

Uvádět pouze instrumenty, u kterých existuje rozumný přenosový mechanismus.

### 5.4 Predikovaný okamžitý směr

Povolené hodnoty:

- UP
- DOWN
- MIXED
- VOLATILITY

VOLATILITY znamená, že hlavní očekávání není čistý směr, ale zvýšený rozsah pohybu.

### 5.5 Mechanismus dopadu

Každý směr musí mít krátké vysvětlení, například:

- vyšší výnosy -> tlak na technologické valuace,
- silnější JPY -> tlak na japonské exportéry,
- ropa nahoru -> vyšší inflační očekávání,
- geopolitická eskalace -> safe-haven poptávka po zlatu,
- slabší ekonomická data -> nižší očekávané sazby,
- dražší energie -> tlak na evropské průmyslové firmy.

### 5.6 Confidence

Používat stupnici 1 až 10.

Confidence nesmí být jen subjektivní pocit. Postupně se musí kalibrovat podle skutečné historické úspěšnosti.

### 5.7 Invalidation condition

Každá směrová predikce musí obsahovat hlavní podmínku, která může daný scénář zneplatnit.

Příklad:

- predikce XAUUSD UP kvůli eskalaci konfliktu,
- invalidace: rychlá diplomatická deeskalace nebo prudký růst reálných amerických výnosů a USD.

### 5.8 Dva časové horizonty

Každá analýza musí oddělit:

1. Immediate reaction — bezprostřední reakce.
2. Next-session follow-through — možnost pokračování pohybu během následující obchodní seance.

---

## 6. Časové horizonty pro vyhodnocení

Pro každou predikci se má zaznamenat cena instrumentu v čase vytvoření predikce a následně minimálně:

- T+15m
- T+1h
- T+4h
- T+1 session / následující relevantní obchodní seance

Později lze přidat:

- T+30m
- T+2h
- T+8h
- T+24h

Je nutné správně pracovat s obchodními hodinami jednotlivých indexů a nepovažovat zavřený trh za nulovou reakci.

---

## 7. Co se má ukládat k cenám

U každého instrumentu a horizontu se mají ukládat alespoň:

- prediction_price — cena v okamžiku predikce,
- evaluation_price — cena při vyhodnocení,
- absolute_change,
- percentage_change,
- direction_actual,
- prediction_correct,
- maximum_favorable_excursion (MFE),
- maximum_adverse_excursion (MAE),
- realized_volatility / rozsah pohybu, pokud je dostupný.

Pro MIXED a VOLATILITY se nesmí používat stejná logika úspěchu jako pro UP/DOWN.

---

## 8. Pravidla vyhodnocování směru

### UP

Predikce je směrově správná, pokud je cena v daném vyhodnocovacím horizontu nad referenční cenou alespoň o minimální definovaný threshold.

### DOWN

Predikce je směrově správná, pokud je cena pod referenční cenou alespoň o minimální threshold.

### MIXED

MIXED se má hodnotit podle toho, zda nevznikl stabilní jednoznačný pohyb a zda byly přítomny protichůdné faktory očekávané v predikci.

### VOLATILITY

VOLATILITY se hodnotí podle skutečného cenového rozpětí nebo realized volatility oproti běžnému historickému rozsahu instrumentu.

Thresholdy nemají být stejné pro všechny instrumenty. Mají být odvozené například z ATR nebo historické volatility.

---

## 9. Kontext trhu, který se má ukládat

Samotný headline často nestačí. Pokud jsou data dostupná, má predikce obsahovat kontext v čase signálu:

- DXY / síla USD,
- US 2Y yield,
- US 10Y yield,
- relevantní lokální státní výnosy,
- Brent / WTI,
- USDJPY,
- VIX,
- současný risk-on / risk-off režim,
- stav hlavních akciových futures,
- vzdálenost ceny od významného intradenního pohybu,
- zda je trh otevřený nebo zavřený,
- čas do otevření hlavní seance.

Důvod: stejná zpráva může mít jiný efekt v různém tržním režimu.

---

## 10. Statistiky projektu

Systém má postupně počítat minimálně:

- celkový počet predikcí,
- počet predikcí podle instrumentu,
- počet podle kategorie zprávy,
- hit rate UP/DOWN,
- hit rate podle časového horizontu,
- průměrný pohyb po signálu,
- medián pohybu,
- MFE,
- MAE,
- precision podle confidence,
- úspěšnost podle confidence bucketů,
- úspěšnost podle typu zprávy,
- úspěšnost kombinace typ zprávy + instrument,
- úspěšnost podle času dne,
- úspěšnost podle regionu,
- úspěšnost podle tržního režimu,
- sample size každé statistiky.

Nikdy nesmí být prezentována vysoká úspěšnost bez uvedení velikosti vzorku.

---

## 11. Kalibrace confidence

Confidence má být postupně kalibrována podle historie.

Příklad cílové interpretace:

- confidence 5/10 ~ přibližně slabý nebo nejistý edge,
- confidence 7/10 ~ statisticky slušný signál,
- confidence 9/10 ~ velmi silná shoda historických podmínek.

Systém musí sledovat, zda confidence odpovídá realitě.

Pokud například signály s confidence 8/10 dosahují dlouhodobě pouze 55% hit rate, systém musí confidence budoucích podobných signálů snížit.

---

## 12. Učení z historie

Projekt nemá bezhlavě přepisovat pravidla po jednom neúspěšném signálu.

Úpravy predikční logiky se mají dělat až při dostatečném vzorku.

Doporučené principy:

- vždy evidovat sample size,
- oddělovat korelaci od příčinného mechanismu,
- bránit overfittingu,
- testovat změny nejdříve na historických nebo shadow datech,
- nesmazat staré predikce po změně metodiky,
- verzovat predikční model/pravidla.

Každá predikce musí mít prediction_model_version.

Díky tomu bude možné porovnat například verzi 1.0 proti 1.1.

---

## 13. Zákaz hindsight bias

Predikce se po zveřejnění nesmí zpětně upravovat tak, aby vypadala lépe.

Jakmile je predikce vytvořena, její původní:

- směr,
- confidence,
- mechanismus,
- invalidation,
- timestamp

musí zůstat zachované.

Případná oprava musí být vedena jako nová revize nebo nový signál s vlastním timestampem.

---

## 14. Duplicity a návazné zprávy

Každá zpráva má mít event_id nebo vazbu na původní událost.

Například:

- první útok,
- potvrzení útoku,
- odveta,
- diplomatická reakce,
- další vojenská eskalace

mohou patřit do stejného širšího event clusteru, ale každá skutečně nová informace může vytvořit nový prediction event.

Cílem je nezapočítávat deset téměř identických článků jako deset nezávislých úspěšných predikcí.

---

## 15. Doporučená datová struktura

Každý prediction event by měl mít přibližně tato pole:

```json
{
  "prediction_id": "unique-id",
  "event_id": "cluster-id",
  "created_at_utc": "2026-09-02T06:30:00Z",
  "source": "Forex Factory",
  "source_section": "Latest Stories",
  "source_url": "...",
  "headline_original": "...",
  "headline_cs": "...",
  "summary_cs": "...",
  "categories": ["GEOPOLITICS", "ENERGY_OIL"],
  "region": ["US", "MIDDLE_EAST"],
  "model_version": "1.0.0",
  "predictions": [
    {
      "instrument": "XAUUSD",
      "immediate_direction": "UP",
      "next_session_direction": "UP",
      "confidence": 8,
      "mechanism": "safe-haven demand",
      "invalidation": "rapid diplomatic de-escalation",
      "prediction_price": null
    }
  ]
}
```

---

## 16. Doporučená struktura repozitáře

Cílová struktura projektu:

```text
FOREX-NEWS-PREDICTIONS/
│
├── PROJECT_RULES.md
├── README.md
├── CHANGELOG.md
├── requirements.txt
├── .gitignore
│
├── config/
│   ├── instruments.yaml
│   ├── news_categories.yaml
│   └── evaluation.yaml
│
├── data/
│   ├── predictions/
│   ├── evaluations/
│   ├── market_snapshots/
│   └── statistics/
│
├── src/
│   ├── ingestion/
│   ├── prediction/
│   ├── market_data/
│   ├── evaluation/
│   ├── statistics/
│   └── reporting/
│
├── tests/
│
└── docs/
    ├── methodology.md
    ├── scoring.md
    └── data_schema.md
```

Struktura se může vyvíjet, ale změny musí být zdokumentované.

---

## 17. Oddělení částí systému

Projekt má být modulární.

### Ingestion

Získává a deduplikuje zprávy.

### Prediction

Vytváří strukturované predikce.

### Market Data

Doplňuje skutečné tržní ceny a kontext.

### Evaluation

Porovnává predikci se skutečností.

### Statistics

Počítá dlouhodobou úspěšnost a hledá silné/slabé oblasti.

### Reporting

Generuje lidsky čitelné výstupy, tabulky a souhrny.

Jedna část nesmí neřízeně přepisovat data jiné části.

---

## 18. Auditovatelnost

Každý záznam musí být zpětně dohledatelný.

Musí být možné zjistit:

- z jaké zprávy predikce vznikla,
- kdy vznikla,
- podle jaké verze pravidel/modelu,
- jaké ceny byly použity,
- kdy proběhlo vyhodnocení,
- jak přesně byla určena správnost.

Výsledky nesmí být ručně upravovány bez auditní stopy.

---

## 19. Pravidla pro změny metodiky

Každá významná změna musí být zapsána do CHANGELOG.md.

Změny typu:

- nové thresholdy,
- jiný způsob hodnocení MIXED,
- nový datový zdroj,
- změna confidence,
- nový model,
- nový instrument,
- změna časových horizontů

musí zvýšit verzi metodiky/modelu.

---

## 20. Bezpečnost a GitHub

Repozitář je veřejný. Proto do něj nikdy neukládat:

- API klíče,
- hesla,
- broker credentials,
- osobní tokeny,
- soukromé přístupové údaje.

Citlivé hodnoty musí být pouze v lokálních environment variables nebo GitHub Secrets, pokud budou někdy potřeba pro automatizaci datových procesů.

---

## 21. Co projekt NESMÍ dělat

Projekt nesmí:

- automaticky otevírat obchody,
- automaticky zavírat obchody,
- nastavovat SL/TP u brokera,
- spravovat portfolio,
- posílat obchodní příkazy,
- měnit historii predikcí po znalosti výsledku,
- mazat neúspěšné predikce kvůli zlepšení statistik,
- hodnotit predikci jinými pravidly podle toho, jak dopadla.

Výstupem projektu jsou analýzy, predikce, statistiky a výzkum — nikoliv automatická exekuce obchodů.

---

## 22. Hlavní princip projektu

Nejde o to vytvořit co nejvíce predikcí.

Cílem je zjistit:

> Které typy zpráv mají pro který instrument, v jakém tržním režimu a v jakém časovém horizontu skutečně opakovatelnou predikční hodnotu?

Pokud historie ukáže, že určitý typ zprávy pro určitý instrument nemá statistickou hodnotu, systém má raději vracet MIXED, nízkou confidence nebo žádný směrový signál.

Kvalita a kalibrace jsou důležitější než počet signálů.

---

## 23. První fáze projektu

První fáze má být jednoduchá a auditovatelná:

1. Ručně nebo poloautomaticky ukládat relevantní Forex Factory predikce.
2. Ukládat přesný timestamp a strukturovaný směr pro každý instrument.
3. Automaticky doplňovat ceny v definovaných horizontech.
4. Vyhodnocovat správnost.
5. Vytvořit základní statistiky.
6. Až potom řešit pokročilejší automatické zpřesňování predikcí.

Nejdříve musí vzniknout kvalitní historie dat. Bez historie nelze spolehlivě optimalizovat predikční logiku.

---

## 24. Definitivní pravidlo pro budoucí vývoj

Každá nová funkce musí odpovědět alespoň na jednu z těchto otázek:

- Zlepší kvalitu vstupních dat?
- Zlepší objektivitu vyhodnocení?
- Zlepší statistickou kalibraci?
- Pomůže vysvětlit, proč predikce funguje nebo nefunguje?
- Sníží riziko zkreslení, duplicit nebo hindsight bias?

Pokud ne, není pro hlavní účel projektu prioritní.
