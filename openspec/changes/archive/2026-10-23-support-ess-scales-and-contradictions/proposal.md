## Why

A SurveyGuard szabálysémája most egy szintetikus, egyetlen 1–5-ös blokkra (`EXT1`–`EXT4`) és fordított itempárokra épül, a Mahalanobis-távolságot pedig az összes kérdésoszlopon egyben számolja. Valós European Social Survey (ESS) adatnál több, egymástól független 0–10-es skála van (intézményi bizalom, elégedettség), 77/88/99 hiánykódokkal, és az ellentmondások nem fordított párok, hanem tartalmi szabályok (pl. nagyon bízik a politikusokban, de a parlamentben egyáltalán nem). Ahhoz, hogy a motor ilyen adatot értelmesen elemezzen, a sémának skálánként kell gondolkodnia, és az ellentmondásokat explicit szabályként kell megadni.

## What Changes

- **BREAKING** Új szabályséma. A `blocks`, `inverted_pairs` és `thresholds` kulcs megszűnik, helyette:
  - `scales`: névvel azonosított skálák; mindegyiknek van `columns`, `valid_min`, `valid_max`, opcionális `missing_codes`, `irv_threshold` és kötelező `mahalanobis_threshold` mezője;
  - `contradictions`: explicit szabálylista; egy szabály két vagy több feltétel (`column`, `op`, `value`) ÉS-kapcsolata.
  - A régi kulcsokat tartalmazó fájlt a betöltő érthető hibaüzenettel elutasítja; régi formátumot nem fordítunk át.
- **BREAKING** A `config/scale_logic.json` ESS-konfiguráció lesz két skálával: `Trust_Institutions` (`trstprl`, `trstlgl`, `trstplc`, `trstplt`, `trstprt`) és `Satisfaction` (`stflife`, `stfeco`, `stfgov`, `stfdem`), `valid_min` 0, `valid_max` 10, `missing_codes` [77, 88, 99], `id_column` `idno`, és explicit ellentmondásszabályok (köztük `trstplt > 8` ÉS `trstprl < 2`).
- A spike-kalibrációs konfiguráció átköltözik a `config/spike_logic.json` fájlba, az új sémában. A régi `EXT2`/`EXT3` fordított pár két explicit szabályként (high-high és low-low) szerepel benne. A `spike_data.csv`-re épülő regressziós teszt (pontosan 50 Mahalanobis-outlier) ezt használja, és a CLI-összesítő minden száma változatlan marad.
- A straightlining és a Mahalanobis detektor skálánként fut. A Mahalanobis-távolság minden skálán külön kovarianciamátrixból és külön küszöbbel számolódik, a kimenetben skálánként külön távolságoszlop jelenik meg.
- **BREAKING** Új okcímkék a `flag_reasons` oszlopban: `Straightlining_<skála>`, `Mahalanobis_<skála>` (a skála neve szó szerint, pl. `Straightlining_Trust_Institutions`), illetve `Contradiction: trstplt>8 vs trstprl<2`. A régi `Straightlining_Error:<blokk>`, `Mahalanobis_Outlier` és `Logical_Contradiction:<a>/<b>` címke megszűnik.
- **BREAKING** A fordított itempáros ellentmondás-vizsgálat (high/low sáv, `high_min`, `low_max`) megszűnik; helyét az explicit szabályok veszik át.
- A hiánykódok kezelése nem változik: a 77/88/99 a nyers kimenetben megmarad, `Missing_Value` jelölést kap, és cellaszinten kimarad minden detektorból. A sor nem esik ki.
- A három detektor neve (`straightlining`, `logical_contradiction`, `mahalanobis_outlier`), a súlyok kulcsai, a `*_triggered` / `*_available` kimeneti oszlopok és a pontszámítás képlete nem változik, így a CLI-összesítő, a Markdown-jelentés és a GUI szerkezete változatlan.
- Új ESS-szerű szintetikus teszt-adatfájl: `tests/fixtures/ess_mock.csv`. A régi `survey.csv` és `rules.json` fixture helyére ez és az ESS-konfiguráció lép. A meglévő 67 tesztet átírjuk az új sémára és adatra. A cél: a teljes tesztkészlet hiba nélkül fusson.
- A `run_spike.py` az új dataclassokra áll át. A korábbi fordított párokat explicit high-high és low-low szabályként fejezi ki, így a kiírt arányok nem változnak.
- README: a szabályséma leírása és a példák ESS-re frissülnek.

## Capabilities

### New Capabilities

<!-- Nincs új capability. -->

### Modified Capabilities

- `survey-quality-detection`: skálaalapú szabályséma (`scales`, `valid_min`/`valid_max`, `missing_codes`), skálánkénti straightlining és Mahalanobis skálanévvel ellátott okokkal, explicit ellentmondásszabályok a fordított párok helyett, új alapértelmezések, a régi séma elutasítása, ESS-szerű teszt-adatfájl.
- `spike-tooling`: a spike-kalibrációs konfiguráció külön fájlba kerül az új sémában, és a `spike_data.csv`-n mért eredmények változatlanok maradnak.

## Impact

- Kód: `surveyguard/config.py` (új dataclassok és validáció), `surveyguard/detectors.py`, `surveyguard/scoring.py`, `run_spike.py`. A `surveyguard/reporting.py`, `surveyguard/cli.py` és `app.py` nem változik, mert a detektornevek és az oszlopnevek megmaradnak. A `surveyguard/io.py` egy kis kiegészítést kap (a megvalósítás közben derült ki): `.sav` bemenetnél az egész értékű numerikus `id_column` egész számként töltődik be, így az `idno` `1026` és nem `1026.0`.
- Konfiguráció: `config/scale_logic.json` (ESS), új `config/spike_logic.json`.
- Tesztek: `tests/test_core.py`, `tests/test_cli.py`, `tests/test_app.py`, `tests/test_reporting_api.py`, `tests/test_real_world.py`. Új `tests/fixtures/ess_mock.csv`. A `tests/fixtures/survey.csv` és `rules.json` törlődik vagy lecserélődik. A `test_spike_scripts.py` nem változik.
- Felhasználók: a meglévő, régi sémájú szabályfájlok nem tölthetők be többé, és a `flag_reasons` szövegére épülő utófeldolgozás új címkéket lát. Új függőség nincs.
