## 1. Alapállapot (a régi kóddal, implementáció előtt)

- [x] 1.1 Valós ESS2 alapállapot a scratchpadbe, háttérben, mert kb. 400 s (design D8/1). Parancs: `python detect_anomalies.py "C:\Users\Gergő\Downloads\ESS2_HU_weighted.sav" --rules config/ess2.json --output <scratch>/ess2_before.csv --report <scratch>/ess2_before.md`, a stdout `<scratch>/ess2_before_summary.txt`-be, a futásidő `Measure-Command`-dal. Ellenőrzés:
  - a három fájl létezik, a SHA-256-jaik `<scratch>/hashes_before.txt`-ben;
  - a számok egyeznek a design „Context” részének smoke-táblázatával (a `PLANNING_LOG.md` 2026-10-24-es „Smoke check” sora): 1498 feldolgozott / 10 gyanús / 160 detektor által jelölt / 81 straightlining / 24 ellentmondás / 65 Mahalanobis / 1498 missing / 0 invalid / átlag 96.22 / minimum 33.33;
  - a `.sav` fájlt csak olvastuk.
- [x] 1.2 Regressziós alapállapot a scratchpadbe:
  - a spike (`spike_data.csv` + `config/spike_logic.json`) és az ess_mock (`tests/fixtures/ess_mock.csv` + `config/scale_logic.json`) CLI-összefoglalója, pontozott CSV-je és `--report` fájlja SHA-256-tal;
  - a `python run_spike.py` kimenete;
  - a `python -m pytest -q` összideje és tesztszáma.

  Ellenőrzés: 162 teszt zöld, és a két riporthash egyezik a design „Context” részében rögzítettekkel (a `PLANNING_LOG.md` 2026-10-24-es „New CLI `--report` reference SHA-256” sora):
  - spike: `1e12cbf72a5b978fe9d061d3b97b390326766b60030862edf714ad85e9521a1d`;
  - ess_mock: `b71c80428efbd07caadf52cb795327a459d4bb06a7846bc26ece94e73ff78c3d`.

## 2. SPSS-metaadat (külön commit, a `PLANNING_LOG.md` 2026-10-24-es „Commit order” sora szerint)

- [x] 2.1 `surveyguard/io.py`: a `load_input` a beolvasás után `frame.attrs = {}` minden formátumnál (design D1). Ellenőrzés: a `.sav` futás az 1.1-es paranccsal, `<scratch>/ess2_after_attrs.*` kimenettel:
  - a pontozott CSV és a riport SHA-256-ja egyezik az 1.1-gyel;
  - az összefoglaló a kimeneti útvonalon kívül azonos;
  - a futásidő a `PLANNING_LOG.md`-be kerül.
- [x] 2.2 Új tesztek a `tests/test_fast_scoring.py`-ban:
  - `.sav` betöltés után az `attrs` `{}`, a nyers kódok változatlanok;
  - a `.csv` és a `.xlsx` betöltés után is `{}`;
  - a `.sav`-ból és a vele egyenértékű `.csv`-ből pontozott keret `to_csv` szövege azonos.

  A `.sav`/`.xlsx` fájlt a teszt generálja `tmp_path`-ba az `ess_mock.csv`-ből, címkékkel (pyreadstat `column_labels`, `variable_value_labels`), hogy az `attrs` tényleg tele legyen a javítás nélkül. Ellenőrzés: a `.sav` teszt a 2.1 nélkül bukik (egyszeri piros futás, a `PLANNING_LOG.md`-be), vele zöld.

## 3. Vektorizált pontozás

- [x] 3.1 `surveyguard/detectors.py`: `straightlining_irvs(frame, scales)` és `contradiction_matches(frame, rules)` a design D2 szerint. A `straightlining`, a `logical_contradictions`, az `irv` és a `mahalanobis` egy betűt sem változik. Ellenőrzés: `git diff surveyguard/detectors.py` csak hozzáadást mutat.
- [x] 3.2 `surveyguard/scoring.py`: a `_data_quality_markers(frame, rules)` oszlopszinten (design D4), a régi `_data_quality` kikerül. Ellenőrzés: a 3.4 tesztjei zöldek.
- [x] 3.3 `surveyguard/scoring.py`: a `score_run` a design D3 szerint előszámolt tömbökkel és egy listaalapú soronkénti összeállítással. Nincs `iterrows`, `iloc` vagy `row[...]` a ciklusban. A `_scale_runs` straightlining-száma maszkösszegből jön. A `score_run`, `score_dataframe`, `aggregate_score`, `ScoringRun`, `ScaleRun` aláírása változatlan. Ellenőrzés:
  - a teljes meglévő tesztkészlet változatlanul zöld;
  - a spike és az ess_mock összefoglalója, pontozott CSV-je és riportja bájtra egyezik az 1.2-vel;
  - a `python run_spike.py` kimenete diff nélkül egyezik.
- [x] 3.4 `tests/test_fast_scoring.py` (design D5):
  - a `_row_reference_score_run` tesztsegéd a `4a63fd3`-as `score_run` ciklus és `_data_quality` szó szerinti másolata, a forráscommit megjelölésével;
  - paraméterezett egyezési teszt: `ess_mock` + `scale_logic.json`, `ess2_mock` + `ess2.json`, `three_scales` + `rules/three_scales.json`, spike + `spike_logic.json` (`to_csv` szövegegyezés és `ScoringRun.scales` egyezés);
  - egy kézzel írt szintetikus keret a D5 szélső eseteivel, köztük egy azonos oszlopot kétszer használó szabállyal és `mahalanobis_min_scales` 2-vel;
  - a két új detektorfüggvény közvetlen összevetése a soronkéntiekkel (IRV `==`, maszkok).

  Ellenőrzés: a teszt zöld, és a `score_run`-ba szándékosan bevitt hiba (pl. fordított okok) mellett piros. Az egyszeri piros futás a `PLANNING_LOG.md`-be kerül, utána a hibát visszaállítjuk.
- [x] 3.5 Valós ESS2: a `.sav` futás az 1.1-es paranccsal, `<scratch>/ess2_after.*` kimenettel. Ellenőrzés: a pontozott CSV és a riport SHA-256-ja egyezik az 1.1-gyel, az összefoglaló a kimeneti útvonalon kívül azonos.

## 4. Mérés, regresszió, záró ellenőrzés

- [x] 4.1 CLI-mérés a valós `.sav`-on (design D7): 3 futás `Measure-Command`-dal, a medián a D7 táblázatba és a `PLANNING_LOG.md`-be. Ellenőrzés: a cél 10 s alatt. Ha nem teljesül, egyeztetünk, mielőtt továbblépünk.
- [x] 4.2 GUI-mérés: egy scratchpad AppTest-szkript feltölti a `.sav`-ot, a „Bundled rules file” → `config/ess2.json`-t választja, és méri a „Run”-tól a kirajzolt eredményig eltelt időt. Az eredmény a D7 táblázatba kerül. Ellenőrzés:
  - a metrikák 1498 / 10 / 96.22;
  - a felhasználó böngészőben is kipróbálja (kézi lépés, eredménye a `PLANNING_LOG.md`-be);
  - a 15 s-os célt a 4.5 értékeli.
- [x] 4.3 Teljes regresszió:
  - `python -m pytest -q` legalább 162 + az új tesztek, zöld, az összidő a D7 táblázatba;
  - `git diff --stat main -- tests/` csak az új `tests/test_fast_scoring.py`-t mutatja;
  - `git diff main -- app.py` üres;
  - a `tests/test_real_world.py` 50 outliert talál;
  - a spike és az ess_mock CLI-kimenetei bájtra egyeznek az 1.2-vel, az ess_mock futásideje a D7 táblázatba;
  - nincs időkorlátos assert (`grep -rn "perf_counter\|time()" tests/` üres).
- [x] 4.4 Takarítás és ellenőrzés:
  - a scratchpad valós adatból készült kimenetei törölve;
  - `git status` csak a tervezett fájlokat mutatja, és a repóban nincs valós adat;
  - `python -m compileall -q surveyguard app.py detect_anomalies.py` és `git diff --check` hiba nélkül fut;
  - `openspec validate speed-up-spss-scoring --strict` hiba nélkül fut;
  - a mért előtte/utána idők a design D7 táblázatában és a `PLANNING_LOG.md`-ben.
- [x] 4.5 Záró döntés a GUI-cache-ről (design D6): ha a 4.2 GUI-mérése 15 s fölött van, egy sor kerül a `PLANNING_LOG.md`-be: a GUI-cache-t külön change-ben kell felvetni, a mért idővel. Ellenőrzés: a sor a `PLANNING_LOG.md` végén van, korábbi sor nem változott.
