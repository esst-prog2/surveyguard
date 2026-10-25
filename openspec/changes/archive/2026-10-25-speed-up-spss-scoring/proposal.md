## Why

A valós ESS2 HU fájl (`ESS2_HU_weighted.sav`, 1498 sor, 604 oszlop) pontozása `config/ess2.json`-nal a CLI-ben 399 s, a webes felületen ugyanennyi. Ebből a betöltés csak 0,4 s, a többi a `score_run`. Két ok van:

1. A `pd.read_spss` a teljes SPSS-metaadatot (oszlopcímkék, value labelek, missing tartományok) a `DataFrame.attrs`-ban hagyja. A pandas ezt minden soronkénti indexelésnél (`iterrows`, `row[columns]`) mélymásolja. A cProfile szerint a futásidő kb. 87%-a `NDFrame.__finalize__` → `copy.deepcopy`. Ha a betöltés után kiürítjük az `attrs`-ot, a futás 64 s, ugyanazokkal az eredményekkel.
2. A maradék 64 s a `score_run` soronkénti Python-ciklusa: `iterrows`, soronkénti `straightlining`, `logical_contradictions` és `_data_quality`, mind kis pandas-objektumokon. A Mahalanobis már vektorizált.

Ugyanez a ciklus lassítja a tesztfutást is (148–159 s). Csak a négy `ess2_mock`-os teszt kb. 67 s.

## What Changes

- **SPSS-metaadat:** a `load_input` betöltés után üríti a `DataFrame.attrs`-ot. A metaadatból semmit nem használunk, így semmi nem vész el.
- **Vektorizált pontozás:**
  - Új keretszintű detektorfüggvények a `surveyguard/detectors.py`-ban: skálánkénti IRV oszlopműveletekkel (`np.var(axis=1)`, csak teljes sorokon), és ellentmondás-szabályonként „értékelhető” meg „teljesül” logikai maszk, a feltételek ÉS kapcsolatával.
  - A soronkénti `straightlining(row, scales)` és `logical_contradictions(row, rules)` aláírása és viselkedése változatlan. A `run_spike.py` és a tesztek ezeket hívják, és ezek adják az egyezési teszt referenciáját is.
  - A `_data_quality` jelölései oszlopszinten készülnek.
  - A `score_run` előre kiszámolt tömbökből állítja össze a kimeneti sorokat. Soronként egyetlen pandas-objektumot sem indexel. A `flag_reasons`, a `detector_details` JSON és minden oszlop bájtra azonos.
- **Webes felület:** az `app.py` nem változik. A GUI ugyanazon a `load_input` → `score_run` úton fut, mint a CLI, így a fenti két javítás ott is hat.
- **Mérés:** az előtte és utána mért idők (CLI, GUI, teljes tesztfutás) a design-ba és a `PLANNING_LOG.md`-be kerülnek. A tesztekben nincs időkorlátos assert.
- **Új tesztek** (`tests/test_fast_scoring.py`):
  - az `attrs` üres `.sav`, `.csv` és `.xlsx` betöltés után, és a `.sav` eredménye azonos a CSV-ével;
  - a vektorizált `score_run` eredménye bájtra azonos a régi soronkénti implementációéval (tesztsegédként megtartva) a meglévő fixture-ökön és egy új, szélső eseteket tartalmazó szintetikus kereten.

  Meglévő teszt nem módosul, és legalább 162 teszt fut.

**Változatlan marad (regresszióvédelem):**
- a spike és az ess_mock CLI-összefoglalója, pontozott CSV-je és `--report` fájlja bájtra (a referencia-hash-eket a design „Context” része szó szerint tartalmazza);
- a `run_spike.py` kimenete, és a `tests/test_real_world.py` 50 outliere;
- a valós ESS2 smoke számai (1498 / 10 / 160 / 81 / 24 / 65 / 1498 / 0 / átlag 96.22 / minimum 33.33), és a teljes pontozott CSV bájtra azonos az `attrs`-javítás előtti futással.

**Non-goals:**
- párhuzamosítás (multiprocessing) és más, nem pandas/numpy alapú gyorsítás;
- a Mahalanobis-számítás módosítása (csak az eredménye olvasását tesszük soronkénti `iloc` helyett tömbből);
- a „nem vonatkozik rá” (6/66) kódok külön kezelése;
- a pontozási logika bármilyen változtatása;
- GUI-eredménycache (`st.cache_data`): a szűrő és a letöltés már ma sem pontoz újra, így a cache csak az ismételt kattintást gyorsítaná, ami a gyorsítás után néhány másodperc. Külön change-ben vesszük elő, ha a GUI-mérés 15 s fölött marad (design D6).

## Capabilities

### New Capabilities

<!-- Nincs új capability. -->

### Modified Capabilities

- `survey-quality-detection`: a betöltött keret nem hordoz fájlmetaadatot, a pontozás oszlopműveletekkel fut, az eredmény bájtra azonos a soronkénti referenciával, és ezt determinisztikus tesztek ellenőrzik.

## Impact

- **Kód:**
  - `surveyguard/io.py`: egy sor a `load_input`-ban;
  - `surveyguard/detectors.py`: két új függvény, a meglévők változatlanok;
  - `surveyguard/scoring.py`: a `score_run` belseje és a `_data_quality` változik, a `score_run`, `score_dataframe` és `aggregate_score` aláírása nem;
  - `app.py`: nem változik.
- **Tesztek:** egy új fájl, a `tests/test_fast_scoring.py`. Meglévő tesztfájl nem változik.
- **Függőség:** nincs új.
- **Dokumentáció:** nem változik, mert a viselkedés sem változik.
- **Adat:** a valós `.sav` fájlt csak olvassuk. Minden kimenet a scratchpadbe kerül, és utána töröljük.
