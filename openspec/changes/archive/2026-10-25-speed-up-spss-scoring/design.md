## Context

A motivációt lásd a proposal.md „Why” részében. Kiindulás: a `feat-ess-modules` ág, a `support-ess-modules-and-scale-aware-scoring` change commitolt állapota (`53543bd`). A `main` (`4a63fd3`) fája ezzel azonos.

**Jelenlegi kód:**
- **`surveyguard/io.py`:** a `load_input` `.sav`-ot `pd.read_spss(source, convert_categoricals=False)`-szal olvas, majd `_whole_number_ids`. Az `attrs`-hoz nem nyúl.
- **`surveyguard/detectors.py`:**
  - a `straightlining(row, scales)` és a `logical_contradictions(row, rules)` egyetlen sort (`pd.Series`) kap, és `DetectorResult`-ot ad;
  - a `mahalanobis(rows, columns, threshold, min_rows)` már keretszintű.
- **`surveyguard/scoring.py`:** a `score_run` a `_normalise_questions` és a `_scale_distances` után `analysis_frame.iterrows()`-zal megy végig a sorokon. Soronként:
  - a két detektort hívja;
  - skálánként `scale_distance.iloc[position]` és `scale_outliers.iloc[position]` olvasás;
  - `aggregate_score`;
  - `_data_quality(frame.iloc[position], ...)`, ami oszloponként egy egyelemű `pd.Series`-t konvertál;
  - egy kimeneti dict, a végén `pd.DataFrame(rows)`.
- **`run_spike.py`:** `frame.apply(lambda row: straightlining(row, ...).triggered, axis=1)`, ugyanígy a `logical_contradictions`-szal. A `tests/test_core.py` közvetlenül hívja a két soronkénti függvényt.
- **`app.py`:**
  - a `run_surveyguard(data_name, data_bytes, rules_bytes=None, *, rules_path=None)` Streamlit-mentes, és a tesztek közvetlenül hívják;
  - a `main()` a `run_key`-t (`data_file.file_id`, rules kulcs) és az eredményt a `st.session_state["surveyguard_run"]`-ban tartja;
  - kattintásra `st.spinner("Processing data...")` alatt fut.

  A szűrő és a letöltés tehát már ma sem pontoz újra. Az újrapontozás csak egy újabb „Run” kattintásra történik.

**Mért kiindulás** (2026-10-24, Windows, Python 3.14, pandas 3.0.2, a felhasználó mérése):
- CLI a valós `.sav`-on 399 s, ebből 0,4 s a betöltés. Az `ess_mock` 4 s.
- A cProfile 150 soron (140 s) kb. 87%-ot mutatott `NDFrame.__finalize__` → `copy.deepcopy` alatt. Ennek 61%-a a `logical_contradictions`-ból, 20%-a a `straightlining`-ból jött.
- `attrs` kiürítése után 64 s, azonos eredménnyel (10 gyanús, 65 Mahalanobis, átlag 96.22).
- Teljes tesztfutás 159 s (162 teszt).

**Saját ellenőrzés a tervezéshez** (2026-10-25, ugyanazon a gépen, scratchpad-szkriptekkel, a `.sav` csak olvasva):
- Az `attrs` 25 kulcsot tartalmaz (`column_labels`, `variable_value_labels`, `missing_ranges`, …), pickle-méretben 237 KB. A `pd.read_csv` utáni `attrs` `{}`.
- A `np.var(matrix, axis=1, ddof=0)` minden skálán bitre ugyanazt adja, mint a soronkénti `irv()`:
  - `ess2_mock` 6126, `ess_mock` 62, spike 987, valós `.sav` 25 521 sor×skála érték, 0 eltérés;
  - 20 000 véletlen, folytonos 21 elemű sor, 0 eltérés.
- A valós `.sav` 127 aktív kérdésoszlopa mind `float64`, egyik sem object.
- `python -m pytest -q --durations=25` → 162 passed, 148 s. A leglassabbak:

  | Teszt | Idő |
  | --- | --- |
  | `test_bundled_modular_rules_match_cli_report` | 33,6 s |
  | `test_ess2_mock_triggers_every_contradiction_rule` | 15,1 s |
  | `test_app_names_skipped_scales_and_rules` | 9,7 s |
  | `test_ess2_core_only_data_skips_every_rotating_scale` | 8,7 s |
  | `test_cli_processes_xlsx_and_sav_inputs` | 7,7 s |
  | `test_cli_creates_derived_scored_csv_and_summary` | 6,8 s |

  A CLI-subprocess tesztek egyenként kb. 3 s-ot töltenek Python-indulással és importokkal (pandas, SciPy, pyreadstat). Ez a rész nem csökken.

**Referenciák** (szó szerint, hogy az ellenőrzés ne függjön a log szerkezetétől):
- **`--report` SHA-256 (Windows, CRLF).** Forrás: a `PLANNING_LOG.md` 2026-10-24-es „New CLI `--report` reference SHA-256” sora.
  - spike (`spike_data.csv` + `config/spike_logic.json`): `1e12cbf72a5b978fe9d061d3b97b390326766b60030862edf714ad85e9521a1d`;
  - ess_mock (`tests/fixtures/ess_mock.csv` + `config/scale_logic.json`): `b71c80428efbd07caadf52cb795327a459d4bb06a7846bc26ece94e73ff78c3d`.
- **Valós ESS2 smoke** (`ESS2_HU_weighted.sav` + `config/ess2.json`). Forrás: a 2026-10-24-es „Smoke check `python detect_anomalies.py ESS2_HU_weighted.sav`” sor.

  | Mutató | Érték |
  | --- | --- |
  | feldolgozott | 1498 |
  | gyanús | 10 |
  | detektor által jelölt | 160 |
  | straightlining | 81 |
  | ellentmondás | 24 |
  | Mahalanobis (m = 3) | 65 |
  | missing | 1498 |
  | invalid | 0 |
  | átlag | 96.22 |
  | minimum | 33.33 |

## Goals / Non-Goals

**Goals:**
- A CLI és a GUI a valós `.sav`-on gyors, a tesztfutás érezhetően rövidebb. A GUI-t is a D1–D4 gyorsítja, mert ugyanazon a `load_input` → `score_run` úton fut. Ezt a D7 GUI-mérése ellenőrzi.
- Minden kimenet bájtra azonos: pontozott CSV, `flag_reasons`, `detector_details` JSON, CLI-összefoglaló, riport, GUI-táblák és letöltések.
- A publikus API (`straightlining`, `logical_contradictions`, `mahalanobis`, `irv`, `aggregate_score`, `score_run`, `score_dataframe`, `load_input`, `run_surveyguard`) aláírása és viselkedése nem változik.
- Az egyezést egy determinisztikus teszt bizonyítja a régi soronkénti implementációval szemben.

**Non-Goals** (a kérés non-goal listáján túl):
- Az `aggregate_score` vektorizálása. Soronként tiszta Python, kb. 1500 hívás ezredmásodpercekben, és így a lebegőpontos műveleti sorrend garantáltan azonos marad (D3).
- A riport, a CLI-összefoglaló és a GUI-táblák gyorsítása: ezek nem szerepelnek a profilban.
- A CLI-subprocess tesztek indulási idejének csökkentése.

## Decisions

### D1. SPSS-metaadat eldobása a `load_input`-ban

A `load_input` a beolvasás után, a `resolve_rules` és a `_whole_number_ids` előtt `frame.attrs = {}`-t állít, **minden formátumnál**. CSV-nél és XLSX-nél ez nem csinál semmit, mert ott az `attrs` eleve üres. A jövőben egy másik olvasó vagy pandas-verzió sem csempészhet így metaadatot a pontozásba.

Miért nem csak `.sav`-nál: egy sor, nincs elágazás, és a spec így egyszerűen kimondható („a betöltött keret nem hordoz fájlmetaadatot”).

Miért nem a `score_run` elején: a GUI és a CLI is a `load_input`-on megy át, a `score_run` viszont publikus, és a hívó keretét nem módosíthatja. A `score_run` amúgy is másolattal dolgozik (`frame.copy()`). A D3 után soronként nem indexel pandas-objektumot, így egy `attrs`-szal érkező keret sem lassítja érdemben.

### D2. Új keretszintű detektorfüggvények, a soronkéntiek változatlanok

*Felhasználói döntés (Q1).* A `surveyguard/detectors.py` két új függvényt kap. A `straightlining(row, scales)` és a `logical_contradictions(row, rules)` egy betűt sem változik.

```python
def straightlining_irvs(frame: pd.DataFrame, scales: dict[str, ScaleConfig]) -> dict[str, pd.Series]:
    """IRV per straightlining scale, in scale order; NaN where any item of the scale is missing."""

def contradiction_matches(
    frame: pd.DataFrame, rules: Iterable[ContradictionRule]
) -> list[tuple[pd.Series, pd.Series]]:
    """Per rule, in rule order: (evaluable, triggered) boolean masks."""
```

**`straightlining_irvs`:**
- csak a `scale.runs_straightlining` skálák;
- `values = frame[list(scale.columns)].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)`;
- `complete = ~np.isnan(values).any(axis=1)`;
- a teljes sorokra `np.var(values[complete], axis=1, ddof=0)`, a többi NaN.

A jelzés a hívónál `irv <= scale.irv_threshold` (NaN → nem jelez). Ez ugyanaz, mint a soronkénti `value <= scale.irv_threshold`. A bitre azonosságot a Context mérése mutatja, és az új egyezési teszt (D5) őrzi.

**`contradiction_matches`:** szabályonként
- a `rule.columns` oszlopai `pd.to_numeric(errors="coerce")`-szal;
- `evaluable = values.notna().all(axis=1)`;
- `triggered = evaluable & cond_1 & … & cond_n`, ahol `cond_i = _COMPARISONS[op](values.iloc[:, i], value)`.

A meglévő `_COMPARISONS` operátorokat használjuk, és a feltételek az `enumerate(rule.conditions)` sorrendjében, oszloppozíció szerint (`iloc`) párosulnak, mint a soronkéntinél. Egy oszlop két feltételben is szerepelhet. A NaN-os sor a maszkban hamis, és a `& evaluable` miatt kimarad, ahogy most.

Miért nem a soronkéntiek átírása: a `run_spike.py` és a `tests/test_core.py` változatlanul fut, és a soronkénti függvények adják a D5-ös referenciát. Ára, hogy a detektorlogika két alakban él. Ezt a D5 egyezési tesztje köti össze.

### D3. A `score_run` szerkezete

A `score_run` aláírása, a `ScoringRun` és a `ScaleRun` nem változik. A futás:

1. A `resolve_rules`, a `_normalise_questions` és a `_scale_distances` változatlan.
2. Előszámítás, mind NumPy-tömbként:
   - a `straightlining_irvs(analysis_frame, active.scales)` skálánkénti IRV-tömbjei és jelzései;
   - a `contradiction_matches(analysis_frame, active.contradictions)` maszkjai;
   - a Mahalanobis-távolságok és -jelzések `.to_numpy()`-jal, egyszer. A számítás nem változik, csak az olvasás: soronkénti `iloc` helyett tömbindex;
   - a `_data_quality_markers(frame, active)` (D4) soronkénti szövegei.
3. Egy egyszerű `for position in range(len(frame))` ciklus listákon és tömbökön. Soronként ugyanazt a `DetectorResult`-hármast építi, ugyanabban a sorrendben (straightlining, logical_contradiction, mahalanobis_outlier), ugyanazokkal a mezőkkel:
   - straightlining: `available` = van teljes futó skála; okok skálasorrendben; `details["irv"]` a teljes skálák `float` értékei skálasorrendben;
   - ellentmondás: okok szabálysorrendben;
   - Mahalanobis: a mai logika.

   Ezután ugyanaz az `aggregate_score` hívás jön, és ugyanaz a kimeneti dict, ugyanazokkal a kulcsokkal és sorrenddel. A végén ugyanaz a `pd.DataFrame(rows)` és `pd.concat`.
4. A `_scale_runs` straightlining-számai a skálánkénti jelzésmaszk összegéből jönnek, a `straightlining_reasons` lista helyett. A szám ugyanaz: hány sor kapta a `Straightlining_<skála>` okot.

**Miért marad egy soronkénti ciklus:** az okok szövege, a `detector_details` JSON és az `aggregate_score` lebegőpontos műveleti sorrendje így garantáltan változatlan, és a `pd.DataFrame(rows)` ugyanazokat a dtype-okat adja. Ez számít például a csupa `None` `quality_score` oszlopnál. A lassúságot nem a Python-ciklus okozta, hanem a soronkénti pandas-objektumok: `iterrows`, `row[columns]`, egyelemű `pd.Series`, `iloc`. Ezek mind kikerülnek. Becslés: 1498 sor × 22 skála tömbolvasással és egy `json.dumps` soronként néhány tized másodperc. A tényleges számot a D7 mérése adja.

**Típusok a JSON-ban:** az IRV-értékek ma Python `float`-ok (`irv()` → `float(...)`), most `tolist()`-ből is azok. A távolságok ma `np.float64`-ek (az `iloc`-ból), most `tolist()`-ből Python `float`-ok lesznek. A `json.dumps` mindkettőt `float.__repr__`-rel írja (`np.float64` a `float` alosztálya), a NaN mindkét esetben `NaN`. A JSON így bájtra azonos. A D5 tesztje ezt is összeveti.

### D4. `_data_quality` oszlopszinten

Az új privát `_data_quality_markers(frame, rules) -> list[str]` a nyers kereten dolgozik, a `rules.question_columns` oszlopain, mint ma. Oszloponként:
- `raw = frame[column]`, `value = pd.to_numeric(raw, errors="coerce")`;
- `missing |= value.isna() & (raw.isna() | raw.eq(""))`;
- `invalid |= value.isna() & ~(raw.isna() | raw.eq(""))`;
- `missing |= value.isin(scale.missing_codes)`;
- `invalid |= value.notna() & ~value.isin(scale.missing_codes) & ((value < valid_min) | (value > valid_max))`.

Soronként a szöveg: `"Invalid_Value;Missing_Value"`, `"Invalid_Value"`, `"Missing_Value"` vagy `""`. Ez pontosan a `";".join(sorted(set(markers)))` négy lehetséges értéke. A régi `_data_quality(row, rules)` kikerül a `scoring.py`-ból, mert privát; szó szerinti másolata a D5 tesztsegédjében marad referenciának.

**Kockázat:** a `pd.to_numeric` egy egész object oszlopon elvben másképp következtethet típust, mint egyelemű Seriesen (pl. vegyes `bool`/`str` cellák). A valós és a fixture-adatban ilyen nincs: a `.sav` kérdésoszlopai `float64`-ek, a CSV-k numerikusak vagy `str`-esek. A D5 szintetikus kerete mégis tartalmaz vegyes object oszlopot (`"refused"`, `""`, `None`, `"5"`, `5`, `11`, `77`), hogy egy eltérés kiderüljön.

### D5. Egyezési teszt a régi soronkénti implementációval

Új fájl: `tests/test_fast_scoring.py`. Egy tesztsegéd (`_row_reference_score_run`) a `4a63fd3`-as `score_run` ciklusának és `_data_quality`-jának szó szerinti másolata. A változatlan, soronkénti `straightlining`/`logical_contradictions` függvényt és a változatlan `aggregate_score`-t hívja, és a régi `scored` keretet adja.

Esetek, mindegyikben `scored.to_csv(index=False)` szövegegyezés, és a `ScoringRun.scales` egyezése:
- `ess_mock.csv` + `config/scale_logic.json`;
- `ess2_mock.csv` + `config/ess2.json` (m = 3, minden szabály, `flagged_scales`);
- `three_scales.csv` + `tests/fixtures/rules/three_scales.json`;
- `spike_data.csv` + `config/spike_logic.json`;
- egy kézzel írt szintetikus keret (kb. 12 sor, két skála, egy rule-only változó, három szabály, köztük `==` és ugyanazt az oszlopot kétszer használó feltétel) szélső esetekkel:
  - vegyes object kérdésoszlop (`"refused"`, `""`, `None`, `"5"`, `5`, `11`, `77`);
  - csupa hiányzó sor (nem pontozható);
  - pontos `irv_threshold`-határ;
  - `>`/`>=` határérték;
  - `mahalanobis_min_scales` 2 mellett egy és két jelölt skála.

Egy további teszt közvetlenül a két új detektorfüggvényt veti össze a soronkéntivel ugyanezen a kereten: IRV-értékek `==`-vel, nem közelítéssel, valamint maszkok.

Ezek a meglévő fixture-öket használják, valós adatot nem. A valós `.sav` egyezését a D7 kézi ellenőrzése adja.

### D6. A GUI-cache nem része ennek a change-nek

*Felhasználói döntés, 2026-10-25. Visszavonja az első tervváltozat `st.cache_data`-s D6-ját, és vele a Q2, Q3, Q4, Q7 és Q10 döntést.*

Az `app.py` nem változik. Nincs `cached_run_surveyguard`, konfig-ujjlenyomat, autouse `tests/conftest.py` vagy `tests/test_app_cache.py`.

**Indok:**
- A szűrő és a letöltés már ma sem pontoz újra, mert az eredmény a `st.session_state`-ben van (Context). A cache csak az ugyanazzal a bemenettel való újrakattintást és az A → B → A visszaváltást gyorsítaná.
- A D1–D4 után egy ESS2-futás várhatóan néhány másodperc, így ez a nyereség nem éri meg a többletkódot és a tesztizolációt.

**A GUI gyorsítását a D1–D4 adja, külön GUI-módosítás nem kell:**
- a `run_surveyguard` a feltöltést ideiglenes fájlba írja, és a `load_input`-tal olvassa be, így a D1 `attrs`-ürítése ott is hat;
- a pontozás a `score_run`, így a D2–D4 is hat.

A betöltés 0,4 s, a riport és a tisztított CSV előállítása nem szerepelt a profilban, ezért a GUI-ban nincs más megnevezhető lassú pont.

**Mikor érdemes külön change-ben elővenni:** ha a D7 GUI-mérése a D1–D4 után is 15 s fölött van. Ilyenkor a záró feladat egy sort ír erről a `PLANNING_LOG.md`-be. Az első tervváltozat kulcs- és méretdöntései (Q2, Q3) kiindulópontként szolgálhatnak.

### D7. Mérés és teljesítménycélok

A célok tájékoztatók. Ha a mérés mást mutat, egyeztetünk. A tesztekbe nem kerül időkorlátos assert.

| Mérés | Módszer | Előtte | Cél | Utána |
| --- | --- | --- | --- | --- |
| CLI, valós `.sav`, `config/ess2.json` | `Measure-Command { python detect_anomalies.py <sav> --rules config/ess2.json --output <scratch>/... --report <scratch>/... }`, 3 futás mediánja (falióra, importokkal) | 399 s (felhasználó, 2026-10-24); `attrs` nélkül 64 s. Apply alapállapot (2026-10-25): 444,8 s, részben párhuzamos tesztfutással terhelve; csak D1-gyel 82,2 s | < 10 s | **5,36 s** (medián: 5,28 / 5,36 / 5,42 s), bájtra azonos kimenet |
| GUI, `.sav` feltöltés + beépített `config/ess2.json` | scratchpad AppTest-szkript: feltöltés, rules-választás, a „Run” kattintástól a kirajzolt eredményig (`perf_counter`); kiegészítésül a felhasználó böngészős próbája | ≈ 400 s (ugyanaz a pipeline) | < 15 s | **5,42 s** (AppTest; 1498 / 10 / 96.22); a felhasználó böngészős próbája rendben, megfigyelése szerint 1–2 s |
| Teljes tesztfutás | `python -m pytest -q` összideje | 159 s (felhasználó), 148 s (2026-10-25) | érezhetően rövidebb | **85,4 s**, 171 teszt (ebből kb. 21 s a D5 soronkénti referenciája az `ess2_mock`-on és a spike-on) |
| `ess_mock` CLI | `Measure-Command` | 4 s (felhasználó); 4,17 s (apply alapállapot) | – (tájékoztató) | 3,82 s (Python-indulás és importok) |

A mérések bash `date`-tel készültek a `Measure-Command` helyett, ugyanazzal a falióra-tartalommal (indulás, importok, betöltés, pontozás, kiírás).

Várakozás, nem ígéret:
- a CLI-t az importok (kb. 2 s), a betöltés (0,4 s) és a 604 oszlopos CSV kiírása uralja;
- a tesztfutásból a négy `ess2_mock`-os teszt kb. 67 s-a nagyrészt eltűnik, a CLI-subprocess tesztek kb. 3 s-a marad.

### D8. Bájtra azonosság ellenőrzése

1. **Az apply elején, a régi kóddal** a scratchpadbe:
   - valós `.sav` + `config/ess2.json`: CLI-összefoglaló, pontozott CSV, riport és SHA-256-jaik (ez az `attrs`-javítás előtti futás, kb. 400 s);
   - a spike és az ess_mock összefoglalója, pontozott CSV-je és riportja hash-ekkel (a riporthash-ek egyezzenek a Context „Referenciák” részében szó szerint rögzített értékekkel);
   - a `python run_spike.py` kimenete.
2. **A D1 után:** a `.sav` futás újra. A pontozott CSV, a riport és az összefoglaló (a kimeneti útvonalon kívül) egyezik az 1. lépéssel.
3. **A D2–D4 után:** ugyanez minden bemenetre, valamint a D5 tesztje.
4. **A végén** a scratchpad kimeneteit töröljük. A repóban nem marad valós adat.

## Eldöntendő kérdések és döntések

| # | Kérdés | Lehetőségek | Döntés | Ki döntött |
| --- | --- | --- | --- | --- |
| Q1 | A detektorfüggvények API-ja | (a) a soronkéntiek maradnak, és új keretszintű függvények jönnek; (b) egy implementáció, a soronkénti delegál a keretszintűre | (a), D2. A `run_spike.py` és a tesztek változatlanul futnak, a soronkénti függvény a D5 referenciája | Felhasználó |
| Q2 | A cache kulcsa beépített rules fájlnál | (a) útvonal + a `config/**/*.json` bájtjai; (b) csak útvonal; (c) útvonal + mtime | (a). **Visszavonva 2026-10-25-én (a cache kikerült, D6).** | Felhasználó |
| Q3 | A cache mérete | (a) `max_entries=4`, TTL nélkül; (b) 1; (c) 8 + 1 óra TTL | (a). **Visszavonva 2026-10-25-én (a cache kikerült, D6).** | Felhasználó |
| Q4 | Futásjelzés | (a) a meglévő spinner marad; (b) kétlépéses `st.status` sorszámmal; (c) spinner + utólagos felirat | (a), a cache saját spinnere kikapcsolva. **Visszavonva 2026-10-25-én (a cache kikerült, D6).** Az `app.py` nem változik, így a meglévő „Processing data...” spinner magától marad. | Felhasználó |
| Q5 | Az `attrs` ürítése csak `.sav`-nál vagy mindig | csak `.sav` / minden formátum | minden formátum (D1): CSV-nél és XLSX-nél no-op, de jövőálló, és egyszerűbb a spec | Claude |
| Q6 | Hol él a régi implementáció referenciaként | tesztsegéd / rögzített várt kimenet | szó szerinti másolat tesztsegédként a `tests/test_fast_scoring.py`-ban (D5). Bármely fixture-ön és a szintetikus kereten is összevethető, nem kell kimeneti fájlt karbantartani | Claude |
| Q7 | Cache-izoláció a tesztekben | új `tests/conftest.py` autouse `st.cache_data.clear()` / tesztenkénti kézi ürítés | `conftest.py`. Meglévő tesztfájlt nem kell módosítani. **Visszavonva 2026-10-25-én (a cache kikerült, D6).** | Claude |
| Q8 | A mérés módszere | D7 táblázata | `Measure-Command` 3 futás mediánja a CLI-hez, scratchpad AppTest-szkript a GUI-hoz, pytest összidő | Claude |
| Q9 | A Mahalanobis-eredmény olvasása | soronkénti `iloc` marad / egyszeri `.to_numpy()` | `.to_numpy()`. A számítás változatlan, ezért nem sérti a non-goalt | Claude |
| Q10 | Az adatfájl neve a cache-kulcsban | benne van / csak a bájtok | benne van, mert a letöltési fájlnevek és a betöltő is tőle függnek. **Visszavonva 2026-10-25-én (a cache kikerült, D6).** | Claude |

## Risks / Trade-offs

- [A detektorlogika két alakban él (soronként és keretszinten), és később eltérhet egymástól] → A D5 egyezési tesztje minden fixture-ön és egy szélsőeset-kereten bájtra összeveti a kettőt, a soronkéntit pedig a `run_spike.py` és a meglévő tesztek is használják.
- [A `pd.to_numeric` oszlopszinten másképp következtethet típust, mint egyelemű Seriesen] → D4: a valós adat `float64`, a szintetikus keret vegyes object oszlopot is tartalmaz, és az eltérés a D5-ben bukna ki.
- [A vektorizált `np.var` lebegőpontos sorrendje egy jövőbeli NumPy-verzióban eltérhet a soronkéntitől] → A NumPy pinnelve van (`requirements.txt`). Az egyezést a D5 `==`-vel ellenőrzi, nem közelítéssel, így egy frissítésnél azonnal kiderül.
- [Cache nélkül a GUI minden „Run” kattintásra újrapontoz, ugyanazzal a bemenettel is] → A D1–D4 után ez várhatóan néhány másodperc. Ha a D7 GUI-mérése 15 s fölött marad, a cache külön change-ben jön (D6).
- [A teljesítménycélok gépfüggők] → Tájékoztató értékek egyetlen gépen mérve, nincs időkorlátos assert, és eltérésnél egyeztetünk.

## Migration Plan

1. Alapállapot a scratchpadbe (D8/1). A régi kódú `.sav` futás kb. 400 s, ezért háttérben fut.
2. D1 → ellenőrzés (D8/2), az időt rögzítjük.
3. D2–D5 → ellenőrzés (D8/3), az időt rögzítjük.
4. GUI-mérés (D7). 15 s fölött egy sor kerül a `PLANNING_LOG.md`-be, hogy a cache-t külön change-ben kell felvetni (D6).
5. A mérések bekerülnek a D7 táblázatba és a `PLANNING_LOG.md`-be, a scratchpad kimeneteit töröljük.
6. **Visszaállítás:** külön branch, külön commitok, így `git revert`-tel visszavonható. A sorrend a `PLANNING_LOG.md` 2026-10-24-es „Commit order” sora szerint: először az `attrs`-javítás (a `pd.read_spss` metaadatának ürítése) külön commitban, utána a vektorizálás. Adat- vagy konfigurációs migráció nincs.

## Open Questions

Nincs nyitott kérdés.
- A Q1 a felhasználó döntése, a Q5, Q6, Q8 és Q9 Claude-é.
- A Q2, Q3, Q4, Q7 és Q10 2026-10-25-én visszavonva, mert a cache kikerült (D6).

Minden döntés és visszavonás bekerült a `PLANNING_LOG.md`-be.
