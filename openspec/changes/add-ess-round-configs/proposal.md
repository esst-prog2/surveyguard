## Why

A SurveyGuard jelenleg egyetlen ESS-körhöz (ESS2) szállít beépített szabályfájlt. Az `ess_sav_files/` mappában viszont mind a 11 magyar ESS-kör (ESS1–ESS11) valódi SPSS-adatbázisa megvan, így minden körhöz előállítható egy, a tényleges metaadatokhoz illesztett konfiguráció. A meglévő `config/ess/core.json` csak az ESS2-re illik: a `trstprt`, `partner`, `icptn`, `wkdcpce`, `chldhm` és az emberi értékek itemei több körből hiányoznak (az ESS11 `a` utótaggal nevezi át őket), és mivel `required: true`, változatlan beemelése az ESS2-n kívül minden kört strukturális hibával állítana le. Ha 11 hasonló konfiguráció közül kézzel kell választani, könnyű rossz kört választani egy fájlhoz, és ha az oszlopok nagyrészt egyeznek, a futás hiba nélkül, de rossz kódokkal megy le. Ezt a rendszernek kell kiszűrnie.

## What Changes

- **Új körkonfigurációk:** `config/ess1.json`, `config/ess3.json` … `config/ess11.json` (10 új gyökérfájl). Az ESS2 mintáját követik (`id_column` `idno`, `flag_threshold` 50, `mahalanobis_min_scales` 3, alapértelmezett súlyok, kör-specifikus életkor/születési év ellentmondások), és mindegyik megkapja a saját `essround` értékét.
- **Új közös core modul:** `config/ess/common_core.json`, csak azokkal a skálákkal és változókkal, amelyek mind a 11 körben azonos oszlopösszetétellel szerepelnek (pl. `Social_Trust`, `Satisfaction`, `Immigration_Policy`, `Immigration_Effects`; `agea`, `yrbrn`, `hhmmb`, `gndr2`).
- **Kör-specifikus core modulok:** `config/ess/rN_core.json` (N = 1, 3–11), a körről körre változó összetételű core skálákkal, `module` `core`, `required` `true`. Ha egy core skálának egy körben 3-nál kevesebb iteme van (`Policy_Attitudes` R6–7, `Job_Autonomy` R3, R4, R6–11), abban a körben nincs ilyen skála.
- **Kör-specifikus rotáló modulok:** `config/ess/rN_<téma>.json`, tematikus szociológiai blokkokba rendezett skálákkal, `module` `rotating`, `required` `false`.
- **Explicit ellentmondás-szabályok minden körhöz** az ESS2 családjai szerint (intézményi bizalom, elégedettség, háztartásméret és -összetétel, életkor/születési év), csak olyan változókra, amelyek az adott körben léteznek.
- **Új, opcionális `essround` gyökérkulcs (pozitív egész):** ha meg van adva, az adatban kell lennie `essround` oszlopnak, és minden nem hiányzó értékének egyeznie kell a kulccsal. Ha nem így van, strukturális hiba, a várt és a talált körrel. Ha nincs megadva, nincs ellenőrzés. Beemelt fájlban konfigurációs hiba.
- **ESS2:** a `config/ess2.json` egyetlen változása az `essround: 2`. A `config/ess/core.json` és a `config/ess/r2_*.json` bájtra azonos marad. A `tests/fixtures/ess2_mock.csv` új `essround` oszlopot kap (minden sorban 2). A pontszámok és a meglévő tesztek várt pontozási eredményei nem változnak.
- **GUI:** a „Bundled rules file” lista természetes sorrendet kap (`ess1, ess2, …, ess11, scale_logic, spike_logic`), és automatikusan felkínálja mind a 11 kört.
- **Git-védelem:** a `.gitignore` kiegészül az `ess_sav_files/` mappával és a `*.sav` mintával.
- **Tömeges sémavalidáció:** új `tests/test_all_configs.py`, amely a repó összes `config/**/*.json` szabályfájlját ellenőrzi (gyökérfájlok betöltése, include-útvonalak, skálanév-regex, árva modulok, körönkénti szintetikus futás a megfelelő `essround` oszloppal).
- **Vészjelzés körönként:** a valós próbafutás összesítőjében külön döntésre szánt sor kerül a PLANNING_LOG-ba, ha egy kör gyanús-aránya 2% fölött vagy Mahalanobis-jelölt-aránya 8% fölött van. A konfiguráció ebben a változásban nem hangolódik.
- A generáló és metaadat-elemző szkript a scratchpadben fut, nem kerül a repóba.

## Capabilities

### New Capabilities
<!-- nincs -->

### Modified Capabilities
- `survey-quality-detection`:
  - új követelmények: a 11 körös ESS-konfigurációk, az `essround` körellenőrzés, a valódi `.sav` fájlok verziókezelésből való kizárása és a beépített szabályfájlok tömeges validálása;
  - módosul a „Compose rules from included files” (az `essround` gyökérszintű kulcs) és a „Provide modular ESS round 2 configurations” (`essround: 2`, a fixture `essround` oszlopa);
  - a „Deterministically verify fast scoring” „no pre-existing test SHALL be modified” kitétele szűkül: a korábbi tesztek várt pontozási eredményei nem változhatnak, a beépített fájllistát rögzítő állítás és az ESS2 fixture viszont igen.
- `web-interface`: a „Use bundled rules files” követelmény a beépített fájlokat természetes sorrendben kínálja fel, új forgatókönyvvel mind a 11 ESS-körre.

## Impact

- **Új fájlok:** `config/ess1.json`, `config/ess3.json`–`config/ess11.json`, `config/ess/common_core.json`, `config/ess/rN_core.json`, `config/ess/rN_*.json` rotáló modulok, `tests/test_all_configs.py`.
- **Módosuló kód:**
  - `surveyguard/config.py`: az `essround` kulcs beolvasása és validálása, `ROOT_ONLY_KEYS`, a `RulesConfig` új mezője;
  - `surveyguard/io.py`: az `essround` ellenőrzése a `load_input`-ban;
  - `app.py`: természetes rendezés a `bundled_rules_files`-ban.
- **Módosuló egyéb fájlok:** `config/ess2.json` (egy kulcs), `tests/fixtures/ess2_mock.csv` (egy oszlop), `tests/test_app_modular.py` (a beépített lista elvárt értéke), `.gitignore` (két sor), `README.md`, `PLANNING_LOG.md`.
- **Változatlan:**
  - a detektorok, a pontozás és a riport;
  - a `detect_anomalies.py`;
  - a `config/ess/core.json`, a `config/ess/r2_*.json`, a `config/scale_logic.json` és a `config/spike_logic.json`.
- **Új függőség nincs.** A `pyreadstat` csak a scratchpad-szkripthez kell, és már telepítve van.
- **Adatvédelem:** valódi válaszadói adat nem kerül a repóba.
