## 1. Alapállapot és függőség

- [x] 1.1 Alapállapot rögzítése a scratchpadbe, implementáció előtt:
  - `python -m pytest -q` (91 passed);
  - a `python detect_anomalies.py spike_data.csv --rules config/spike_logic.json --output <scratch>/spike_before.csv` összefoglalója fájlba;
  - a `spike_before.csv` és egy `ess_mock_before.csv` (`tests/fixtures/ess_mock.csv` + `config/scale_logic.json`) teljes SHA-256 hash-e;
  - a `python run_spike.py` kimenete;
  - a CLI `--report` SHA-256 hash-e a spike- és az ess_mock-futásra.

  Ellenőrzés: a négy fájl létezik, és a számok megegyeznek a design „Context” részében rögzítettekkel.
- [x] 1.2 `requirements.txt`: `scipy==1.15.3; python_version < "3.11"` és `scipy==1.17.1; python_version >= "3.11"`. Ellenőrzés: `python -m pip install -r requirements.txt` hiba nélkül lefut, és `python -c "from scipy.stats import chi2; print(round(chi2.ppf(0.95, 5), 6))"` kimenete `11.070498`.

## 2. Konfiguráció: include, változók, új mezők

- [x] 2.1 `surveyguard/config.py`: `load_rules(path, *, allow_include=True)` include-fával a design D1 szerint:
  - mélységi sorrend, relatív útvonalak;
  - körkörös és ismételt include, olvashatatlan beemelt fájl;
  - gyökérkulcs (`weights`, `flag_threshold`, `mahalanobis_min_scales`, `id_column`) beemelt fájlban, régi kulcs bármelyik fájlban;
  - a gyökérszintű `mahalanobis_min_scales` validációja (pozitív egész, alapérték 1);
  - skálanév-, változó- és oszlopütközés mindkét fájl nevével;
  - fájlonkénti szabálypozíció a hibaüzenetben.

  Ellenőrzés: új tesztek a `tests/fixtures/rules/` alatti szintetikus fájlokkal: lánc (`root.json` → `modules/a.json` → `modules/b.json`), körkörös (`circular_a.json` ↔ `circular_b.json`), ütköző skálanév, ütköző oszlop, `flag_threshold` és `mahalanobis_min_scales` beemelt fájlban, `thresholds` beemelt fájlban, hiányzó beemelt fájl; a `mahalanobis_min_scales` `0`, `2.5`, `"3"` és `true` értékre hibát ad. A lánc ugyanazt a `RulesConfig`-ot adja, mint az egyfájlos megfelelője.
- [x] 2.2 `ScaleConfig` új mezői alapértékkel a design D3 szerint (`module`, `required`, `detectors`, `min_items_straightlining`, `mahalanobis_min_rows_per_item`, `threshold_source`), `mahalanobis_threshold: float | None`, és a hozzájuk tartozó validáció. Ellenőrzés:
  - a meglévő `test_optional_rule_settings_use_documented_defaults` és a `run_spike.py` változatlanul fut;
  - új paraméterezett teszt az érvénytelen `detectors`, `min_items_straightlining` és `mahalanobis_min_rows_per_item` értékekre.
- [x] 2.3 `mahalanobis_alpha` a design D4 szerint: pontosan egy a küszöb és az alpha közül, ha van Mahalanobis detektor, egyik sem, ha nincs; a küszöb `chi2.ppf(1 - alpha, df=itemszám)`, a `threshold_source` értéke `alpha=<alpha>`. Ellenőrzés:
  - tesztek: alpha 0.05 öt itemen → `11.070498` (6 tizedesre), és ugyanazok a Mahalanobis-eredmények az ess_mock-on, mint a konfigurált küszöbbel;
  - alpha 0.01 négy itemen → `13.276704`;
  - hiba, ha mindkettő meg van adva, ha egyik sincs, vagy ha Mahalanobis nélküli skálán szerepel bármelyik.
- [x] 2.4 `variables` szakasz (`VariableConfig`) a design D2 szerint. A szabályfeltétel oszlopa skálaoszlop vagy deklarált változó lehet; skálaoszlop és változó nem eshet egybe. Ellenőrzés:
  - a `partner==2 vs dsgrhwk>=1` szabály pontosan ezt az okot adja `partner=2, dsgrhwk=3` esetén;
  - `rshipa2=66` esetén a szabály kimarad, és nincs `data_quality` jelölés;
  - oszlopátfedésnél és nem deklarált oszlopnál a hibaüzenet a szabály pozícióját és fájlját nevezi meg.

## 3. Kihagyás, detektorok, pontozás

- [x] 3.1 `surveyguard/io.py` `resolve_rules(rules, columns)` a design D7 szerint, a `load_input` validálása erre épül. Ellenőrzés: tesztek a következőkre:
  - teljesen hiányzó `required: false` skála: kimarad, név szerint listázva;
  - részben hiányzó opcionális skála: hiba a skála és a hiányzó oszlopok nevével;
  - hiányzó kötelező oszlop: a mai hibaüzenet;
  - minden skála kimarad: hiba;
  - a kihagyott oszlopra hivatkozó szabály kimarad, és listázva van;
  - hiányzó opcionális változó.
- [x] 3.2 `surveyguard/detectors.py`:
  - a `straightlining` csak az értékelhető skálákon fut (nincs kihagyva, a `detectors`-ban szerepel, elér a `min_items_straightlining` határt, a sor teljes), a büntetés 0/1 marad;
  - a `mahalanobis(rows, columns, threshold, min_rows=2)` a minimum alatt üres távolságot ad.

  Ellenőrzés:
  - a meglévő detektortesztek zöldek;
  - új tesztek: 3 itemes skála `min_items_straightlining` 5 mellett nem jelöl, és ha más skála nem értékelhető, a detektor elérhetetlen; `detectors: ["mahalanobis_outlier"]` mellett nincs straightlining-ok; 4 itemes skála `mahalanobis_min_rows_per_item` 10 és 39 érvényes sor mellett nem elérhető, 40 sornál igen; alapértéknél 2 sorral is számol.
- [x] 3.3 `surveyguard/scoring.py`:
  - `score_run(frame, rules) -> ScoringRun` és `ScaleRun` a design D6 szerint;
  - a Mahalanobis detektor csak akkor `triggered` és csak akkor ad `Mahalanobis_<skála>` okot, ha a válaszadó legalább `mahalanobis_min_scales` skálán jelez; a büntetés mindhárom detektornál 0/1;
  - `detector_details.mahalanobis_outlier.flagged_scales` csak `m > 1` esetén;
  - távolságoszlop csak a nem kihagyott, Mahalanobis detektoros skálákra;
  - nincs új kimeneti oszlop; a `score_dataframe` megmarad burkolóként.

  Ellenőrzés: új hármasskálás szintetikus fixture (`tests/fixtures/three_scales.csv` + `tests/fixtures/rules/three_scales.json`, kézzel ellenőrzött értékekkel):
  - m = 3 mellett a két skálán jelző sor nem triggered, nincs `Mahalanobis_` oka, a `flagged_scales` mindkét skálát tartalmazza, a pontszáma 100.00;
  - m = 3 mellett a három skálán jelző sor triggered, három okkal, pontszáma 66.67;
  - m = 3 mellett a csak két értékelhető skálájú, mindkettőn jelző sor elérhető, de nem triggered;
  - m = 1 (alapérték) mellett ugyanezek a sorok a régi „bármelyik skála” eredményt adják;
  - a skálatáblázat `mahalanobis_count` értéke m-től független.
- [x] 3.4 Spike-regresszió. Ellenőrzés:
  - a `python detect_anomalies.py spike_data.csv --rules config/spike_logic.json` összefoglalója bájtra azonos az 1.1-es fájllal;
  - a pontozott CSV SHA-256 hash-e bájtra azonos az 1.1-es mentéssel, és ugyanez igaz az ess_mock pontozott CSV-jére;
  - a `python run_spike.py` kimenete azonos (üres diff);
  - a `tests/test_real_world.py` zöld (50 outlier);
  - új teszt: a spike pontozott kimenetének oszlopai és a `detector_details` kulcsai ugyanazok, mint a változás előtt (nincs `flagged_scales`).

## 4. Riport, CLI és GUI

- [x] 4.1 `surveyguard/reporting.py` a design D8 szerint:
  - `scale_results(run)`;
  - a `render_report`/`write_report` opcionális `run` paramétere a „Scale results” és a „Skipped scales and rules” szakaszhoz;
  - a `print_summary` opcionális `skipped_scales` paramétere a feltételes „Skipped scales:” sorhoz.

  Ellenőrzés:
  - a meglévő `render_report`-golden teszt (`run` nélkül) bájtra azonos;
  - új tesztek: az ess_mock skálatáblázata a design D12 értékeivel; alpha alapú sor `15.086272 (alpha=0.01)`; a kihagyott skála és szabály listázva van; kihagyás nélkül a „Skipped scales:” sor hiányzik; m = 3 mellett a detektortáblázat Mahalanobis-száma az m-et elérő válaszadóké, alatta a `Mahalanobis counts respondents flagged on at least 3 scale(s).` sor, a skálatáblázatban pedig a `Mahalanobis flags (scale-level)` oszlop az összes skálaszintű jelzést számolja.
- [x] 4.2 `surveyguard/cli.py`: a `score_run`-t használja, és átadja a kihagyott skálákat a `print_summary`-nek, a `run`-t a `write_report`-nak. Ellenőrzés:
  - CLI-teszt egy hiányzó rotáló modullal: a `Skipped scales: …` sor és a riportszakasz jelen van;
  - az ess_mock CLI-összefoglalója változatlanul 33 / 3 / 9 / 4 / 4 / 4 / 2 / 2 / 0 / 87.88 / 33.33.
- [x] 4.3 `app.py` a design D9 szerint:
  - „Rules source” rádiógomb (feltöltés vagy beépített `config/*.json`);
  - `run_surveyguard(..., rules_bytes=None, *, rules_path=None)`;
  - feltöltött include → `Error:` üzenet;
  - a `run_key` a forrást is tartalmazza;
  - skálatáblázat, és `st.info` a kihagyott skálákról és szabályokról.

  Ellenőrzés:
  - AppTest-tesztek: a futtatás csak adat és rules forrás mellett engedélyezett; a beépített `config/scale_logic.json` ugyanazt adja, mint a feltöltött; a beépített `config/ess2.json` egyezik a CLI riportjával; feltöltött include-os fájl `Error:`-t ad eredmények nélkül; a skálatáblázat egyezik a riporttal; forrásváltás után eltűnnek a régi eredmények;
  - a meglévő AppTest-tesztek a sidebarban a feltöltés opciót használják.

## 5. Konfigurációs fájlok és fixture-ök

- [x] 5.1 `config/scale_logic.json` és `config/spike_logic.json`: nem változnak. Ellenőrzés: `git diff --exit-code config/scale_logic.json config/spike_logic.json` üres, és az ess_mock gyanús halmaza továbbra is 1026, 1027 és 1032 (mind 33.33).
- [x] 5.2 `config/ess/core.json`, `config/ess/r2_health.json`, `config/ess/r2_econ_morality.json`, `config/ess/r2_family_work.json` és `config/ess2.json` a design D10 és D11 szerint (22 skála, változók, szabályok; core `required: true`, rotáló `required: false`; alpha 0.01, `min_items_straightlining` 5, `mahalanobis_min_rows_per_item` 10; gyökér: `idno`, `flag_threshold` 50, `mahalanobis_min_scales` 3, a korsávszabályok). Ellenőrzés:
  - egy scratchpad-szkript a valós `.sav` metaadataiból (value labels, missing ranges, megfigyelt értékek) ellenőrzi minden skálaoszlop tartományát és missing kódjait, eltérés nélkül; a `.sav` a repóba nem kerül;
  - teszt: a `load_rules("config/ess2.json")` 22 skálát ad a D10-es sorrendben és beállításokkal, `flag_threshold` 50 és `mahalanobis_min_scales` 3 mellett.
- [x] 5.3 Új szintetikus `tests/fixtures/ess2_mock.csv`: egyszeri, rögzített seeddel generált, commitolt fájl legalább 220 sorral, az összes core és rotáló oszloppal és a változókkal. Úgy készül, hogy minden skála elérje a 10 × item sort, és legalább egy-egy sor kiváltsa a D11 szabályait. A seed és a generálás módja a `PLANNING_LOG.md`-be kerül. Ellenőrzés:
  - a CLI `config/ess2.json`-nal hiba nélkül fut rajta;
  - teszt: a csak core oszlopokra szűkített változaton minden rotáló skála megjelenik a `Skipped scales:` sorban;
  - teszt: a mock egy rotáló skálájából két oszlopot törölve hiba keletkezik.
- [x] 5.4 Meglévő tesztek: a várt számaik nem változnak (design D12); csak az AppTest-tesztek sidebar-választása módosulhat a 4.3-as „Rules source” vezérlő miatt. Ellenőrzés:
  - `python -m pytest -q` zöld, és legalább 91 teszt fut;
  - a `git diff` a meglévő tesztfájlokban csak a sidebar-választást érinti, várt szám nem változik.

## 6. Dokumentáció és végső ellenőrzés

- [x] 6.1 README, új szakasz „Modular ESS configuration and scale-aware scoring” címmel:
  - `include` és `variables`;
  - az új skálamezők és alapértékeik;
  - alpha vagy threshold;
  - `required` és a kihagyás (a részleges hiány hiba);
  - a `mahalanobis_min_scales` (m) küszöb: miért nő a „bármelyik skála” téves riasztása a skálák számával, a 0/1 pontozás egy példával, a skálaszintű és a válaszadószintű Mahalanobis-számok különbsége, és hogy m-nél kevesebb értékelhető skálájú válaszadó nem jelölhető;
  - a GUI beépítettkonfig-választója;
  - a viselkedésblokkok kizárása;
  - a magas `Missing_Value` számra vonatkozó figyelmeztetés.

  Ellenőrzés: a README példaparancsai (`config/ess2.json` az `ess2_mock.csv`-n, `config/scale_logic.json` az `ess_mock.csv`-n) hiba nélkül lefutnak.
- [x] 6.2 Kézi smoke check: `python detect_anomalies.py "C:\Users\Gergő\Downloads\ESS2_HU_weighted.sav" --rules config/ess2.json --output <scratch>/ess2_scored.csv --report <scratch>/ess2_report.md`. A gyanúsak arányát, a detektoronkénti és skálánkénti számokat a `PLANNING_LOG.md`-be rögzítjük, és összevetjük három logikával: a régi „bármelyik skála” (m = 1), az elvetett arányos és a választott m = 3 (az m = 1 és az arányos eredményt scratchpad-szkript adja), valamint a design D13-as várt értékeivel (m = 3: 50 alatt 10 gyanús, 65 Mahalanobis-jelölt). Ellenőrzés: a futás 0-s kóddal végződik, a scratch fájlokat utána töröljük, és a repóban nincs valós adat (`git status` csak a tervezett fájlokat mutatja).
- [x] 6.3 Az új CLI `--report` referenciahash-ek (spike, ess_mock) a `PLANNING_LOG.md`-be kerülnek. Ellenőrzés:
  - a GUI-letöltés bájtra azonos a CLI riportjával (a meglévő AppTest-teszt);
  - `python -m compileall -q surveyguard app.py detect_anomalies.py` és `git diff --check` hiba nélkül fut.
- [x] 6.4 `openspec validate support-ess-modules-and-scale-aware-scoring --strict` hiba nélkül lefut.
