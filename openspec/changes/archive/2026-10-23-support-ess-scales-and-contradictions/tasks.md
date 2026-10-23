## 1. Konfigurációs modell

- [x] 1.1 `surveyguard/config.py`:
  - a `BlockConfig`/`PairConfig` helyére `ScaleConfig`, `Condition`, `ContradictionRule` (a `label` tulajdonsággal) és az új `RulesConfig` kerül (`scales`, `contradictions`, `weights`, `flag_threshold`, `id_column`, `question_columns`);
  - a `load_rules` az új sémát olvassa, kötelező skálánkénti `mahalanobis_threshold`-dal, a `contradictions` alapértéke `[]`, a `missing_codes` alapértéke `[]`, az `irv_threshold` alapértéke `0`.

  Ellenőrzés: egy inline ESS-JSON betöltése után a skálák, a feltételek és az alapértékek a vártak, a `ContradictionRule.label` pedig `Contradiction: trstplt>8 vs trstprl<2`.
- [x] 1.2 Validációs hibák a design 4. és 5. pontja szerint: régi kulcs (`blocks`/`inverted_pairs`/`thresholds`), érvénytelen skálanév, `valid_min >= valid_max`, hiánykód a tartományban, duplikált oszlop, hiányzó vagy nem pozitív `mahalanobis_threshold`, egyfeltételes szabály, ismeretlen `op`, nem numerikus `value`, skálán kívüli oszlop. Ellenőrzés: minden esetre egy `pytest.raises(ConfigurationError, match=...)` teszt, ahol az üzenet megnevezi a kulcsot, a skálát, az oszlopot vagy a szabály indexét.

## 2. Detektorok és pontozás

- [x] 2.1 `surveyguard/scoring.py` `_normalise_questions` és `_data_quality`: a `valid_min`/`valid_max`/`missing_codes` mezőket használják, a viselkedés változatlan. Ellenőrzés: egy 88-as és egy 11-es értéket tartalmazó sor a nyers kimenetben megmarad, `Missing_Value`, illetve `Invalid_Value` jelölést kap, és nem esik ki.
- [x] 2.2 `straightlining`: skálánként fut, az ok `Straightlining_<skála>`. A hiányos skálát kihagyja, és a detektor csak akkor elérhetetlen, ha minden skálát kihagyott. Ellenőrzés: tesztek a csak egyik skálán konstans sorra, a mindkét skálán konstans sorra és a hiányos skálára.
- [x] 2.3 Az ellentmondás-detektor (`logical_contradiction`) az explicit szabályokat értékeli a maszkolt soron: a hiányzó oszlopú szabályt kihagyja, több szabály esetén konfigurációs sorrendben ad okot. A régi `logical_contradictions` sávlogika törlődik. Ellenőrzés:
  - `trstplt=9, trstprl=1` esetén pontosan `Contradiction: trstplt>8 vs trstprl<2`;
  - `trstplt=8` esetén nincs ok;
  - `trstprl=77` esetén kihagyja;
  - üres listánál a detektor elérhetetlen.
- [x] 2.4 Mahalanobis: a `score_dataframe` skálánként hívja a `mahalanobis` függvényt, saját érvényes sorhalmazzal és saját küszöbbel.
  - Az ok `Mahalanobis_<skála>`.
  - Skálánként egy `mahalanobis_distance_<skála>` oszlop keletkezik, a régi `mahalanobis_distance` oszlop megszűnik.
  - A `detector_details` JSON-ban `distances` szerepel.
  - A szinguláris mátrix `MathematicalError`-t ad a skála nevével.

  Ellenőrzés: tesztek a centroid sorra (0), a csak egyik skálán outlier sorra, a hiányos skálájú sorra (az egyik oszlop üres, a másik nem) és a szinguláris skálára (az üzenetben szerepel a skála neve).
- [x] 2.5 Pontozás: detektoronként 0/1 penalty, az aggregálás változatlan. Ellenőrzés: a két skálán straightlining-oló, egyébként tiszta sor mindkét okot megkapja, a `quality_score` értéke `66.67`.

## 3. Konfigurációs fájlok és fixture

- [x] 3.1 `config/scale_logic.json` cseréje az ESS-konfigurációra a design 8. pontja szerint (`idno`, két skála, 0–10, 77/88/99, χ²₀.₉₅ küszöbök: `11.070498` és `9.487729`, három szabály). Ellenőrzés: a `load_rules` hiba nélkül betölti.
- [x] 3.2 Új `config/spike_logic.json` a design 9. pontja szerint. Ellenőrzés: a `python detect_anomalies.py spike_data.csv --rules config/spike_logic.json` összesítője megegyezik a `spike-tooling` delta baseline-számaival (1000 / 2 / 181 / 20 / 140 / 47 / 0 / 13 / 13 / 96.61 / 0.00).
- [x] 3.3 Új `tests/fixtures/ess_mock.csv` a design 10. pontja szerint, `idno`, `cntry` és a 9 item oszlopokkal. Ellenőrzés: egy egyszeri `score_dataframe`-futás a `config/scale_logic.json`-nal hiba nélkül lefut, és a kijelölt sorok a tervezett okokat kapják. A tényleges számokat (gyanús, skálánkénti és szabályonkénti triggerek, Mahalanobis-outlierek, missing, invalid) kézzel ellenőrizve a PLANNING_LOG-ba kell rögzíteni.
- [x] 3.4 `tests/fixtures/survey.csv` és `tests/fixtures/rules.json` törlése, miután már egyetlen teszt sem hivatkozik rájuk. Ellenőrzés: a `grep -rn "survey.csv\|fixtures/rules.json" tests app.py surveyguard` nem ad találatot.

## 4. Tesztek migrálása

- [x] 4.1 `tests/test_core.py`: a betöltési, validációs és alapértelmezés-tesztek inline ESS-JSON-ra állnak át, a pipeline-tesztek az `ess_mock.csv` + `config/scale_logic.json` párosra. A fordított páros tesztek ellentmondásszabály-tesztekké íródnak át, az új okcímkékkel. Ellenőrzés: `python -m pytest -q tests/test_core.py` zöld.
- [x] 4.2 `tests/test_cli.py` és `tests/test_reporting_api.py`: az ESS-fixture és az új okcímkék használata. A riporttesztek pontos számai az `ess_mock.csv`-ből jönnek. Az `.xlsx`/`.sav` generálás az `ess_mock.csv`-ből történik, nyers kódokkal. Ellenőrzés: a két fájl tesztjei zöldek.
- [x] 4.3 `tests/test_app.py`: a `FIXTURE_RULES`/`FIXTURE_CSV` az ESS-párosra mutat, a CLI–GUI egyenértékűségi és az AppTest-tesztek az új okcímkékkel futnak. Ellenőrzés: `python -m pytest -q tests/test_app.py` zöld.
- [x] 4.4 `tests/test_real_world.py`: a küszöböt a `config/spike_logic.json` skálájából olvassa, és továbbra is pontosan 50-et vár. Ellenőrzés: a teszt zöld. Egy szándékos piros futás (ideiglenesen elrontott küszöbbel) a parancssal és a kimenettel együtt kerül a PLANNING_LOG-ba, majd a küszöb visszaáll.
- [x] 4.6 `surveyguard/io.py`: `.sav` bemenetnél a numerikus `id_column` egész számként töltődik be, ha minden nem hiányzó értéke egész. Ellenőrzés: egy `.sav`-ból betöltött `idno` `1026`, nem `1026.0`, és a `test_excel_and_spss_uploads_match_csv` zöld (a CSV, XLSX és SAV riport azonos).
- [x] 4.5 Új tesztek a specben új vagy módosult forgatókönyvekre, amelyeket a 1.x–2.x feladatok még nem fedtek le, köztük a régi sémájú `blocks`/`inverted_pairs` fájl CLI-futására: kilépési kód 1, `Error:` üzenet, nincs scored output. Ellenőrzés: a teljes tesztszám legalább 67, és minden új teszt zöld.

## 5. Spike-szkript és dokumentáció

- [x] 5.1 `run_spike.py`: áll át `ScaleConfig`/`ContradictionRule` használatára, a két párt négy szabállyal (high-high, low-low) fejezi ki. Ellenőrzés: a `python run_spike.py` kimenete karakterre egyezik a baseline-nal (2.1% / 25.4% / 15.7% / 9.829530 / 5.0%), és a `tests/test_spike_scripts.py` zöld.
- [x] 5.2 README:
  - a szabályséma leírása (`scales`, `contradictions`, mezők és alapértékek);
  - ESS-példa;
  - az okcímkék listája;
  - migrációs bekezdés (régi kulcsok → új séma, fordított pár → két szabály);
  - a spike-futtatás a `config/spike_logic.json`-nal.

  Ellenőrzés: a README-ben lévő példaparancsok a fixture-ön hiba nélkül lefutnak.

## 6. Végső ellenőrzés

- [x] 6.1 `python -m pytest -q`: a teljes készlet zöld. A tesztszám és a futási idő a PLANNING_LOG-ba kerül.
- [x] 6.2 `python detect_anomalies.py tests/fixtures/ess_mock.csv --rules config/scale_logic.json --report <scratch>/ess.md`, valamint ugyanez a GUI-ban (AppTest vagy `streamlit run`). Ellenőrzés: a két riport bájtra azonos, és tartalmazza a `Straightlining_Trust_Institutions`, `Straightlining_Satisfaction` és `Contradiction: trstplt>8 vs trstprl<2` okokat.
- [x] 6.3 `openspec validate support-ess-scales-and-contradictions --strict` hiba nélkül lefut.
