## 1. Előkészítés és git-védelem

- [x] 1.1 Munka a meglévő `feat-all-ess-rounds` ágon; ellenőrzés: `git branch --show-current` kimenete `feat-all-ess-rounds`
- [x] 1.2 A `.gitignore` kiegészítése az `ess_sav_files/` és a `*.sav` sorral; ellenőrzés: a `git status --ignored` a 11 `.sav` fájlt ignoráltként mutatja, a `git ls-files "*.sav"` üres
- [x] 1.3 Kiinduló állapot rögzítése a PLANNING_LOG-ba: `pytest -q` (171 teszt), a `config/ess2.json`, `config/ess/core.json`, `config/ess/r2_*.json` SHA-256 hash-e, valamint a valódi ESS2 fájl CLI-eredménye és pontozott CSV-hash-e a `config/ess2.json`-nal; ellenőrzés: az ESS2-számok 1498 / 10 / 160 / 81 / 24 / 65 / 1498 / 0 / 96.22 / 33.33

## 2. `essround` körellenőrzés (kód)

- [x] 2.1 `surveyguard/config.py`: `"essround"` a `ROOT_ONLY_KEYS`-be, `RulesConfig.essround: int | None = None`, validálás a `_positive_int`-tel; ellenőrzés: tesztek a `0`, `"3"`, `2.5` értékre és a beemelt fájlban álló kulcsra, a hibaüzenetek a spec szerint
- [x] 2.2 `surveyguard/io.py`: `_check_essround(frame, rules)` a `load_input`-ban a `resolve_rules` után (nincs oszlop, csak üres, eltérés; számként összehasonlítva, egészek tizedes nélkül); ellenőrzés: `tests/test_essround.py` egyező, eltérő (pontos üzenet), hiányzó, üres oszlop, kulcs nélküli konfig és SPSS-ből jövő `2.0` esetre, plus szándékos piros futás az ellenőrzés kikapcsolásával, majd visszaállítás
- [x] 2.3 CLI és GUI hibaút; ellenőrzés: CLI-teszt (kilépési kód 1, nincs pontozott kimenet, az üzenet a standard kimeneten, ahogy a CLI minden hibát kiír) és AppTest (`essround` 4 + beépített `config/ess3.json` → ugyanaz az üzenet, nincs eredmény)
- [x] 2.4 ESS2 a (b) változat szerint: `"essround": 2` a `config/ess2.json`-ba, `essround` oszlop (minden sorban 2) a `tests/fixtures/ess2_mock.csv` végére, `assert rules.essround == 2` a `test_ess2_configuration_loads_with_documented_settings`-be; ellenőrzés: a `git diff main -- config/ess2.json` csak ezt az egy kulcsot mutatja, a `core.json` és az `r2_*.json` hash-e egyezik az 1.3 értékeivel, és minden ESS2-teszt a régi várt pontozási eredményekkel zöld

## 3. Metaadat-elemzés (csak scratchpad)

- [x] 3.1 Metaadat-kivonat mind a 11 körről (`metadataonly=True`); ellenőrzés: a sor- és oszlopszámok megegyeznek a design táblázatával
- [x] 3.2 Oszloponkénti nem hiányzó magyar darabszám (csak összesítő), körönként Y = max(`agea + yrbrn`) és az `essround` egyedi értékei; ellenőrzés: az Y értékek megegyeznek a design táblázatával, és minden fájl `essround`-ja csak a saját kör száma
- [x] 3.3 A közös core halmaz és a körönkénti core skálák meghatározása a D1 szerint (3 itemnél rövidebb core skála kimarad: `Policy_Attitudes` R6–7, `Job_Autonomy` R3, R4, R6–11); ellenőrzés: a lista megfelel a D1-nek, vagy az eltérés a PLANNING_LOG-ba kerül
- [x] 3.4 Jelöltblokkok és szűrés a D4 szerint, kézi blokktérkép körönként (skálanév → oszlopok, téma → fájl), a labelek áttekintő listájával a scratchpadben; ellenőrzés: nincs országspecifikus, háztartási-tábla- vagy gyakoriságblokk, nincs 50% alatti kitöltöttségű és nincs 3 itemnél rövidebb skála
- [x] 3.5 Skálánkénti straightlining-arány (csak összesítő) a D5 detektorválasztáshoz, és az `icpart1` kódolásának ellenőrzése a value labelekből; ellenőrzés: minden 5% feletti skála csak `mahalanobis_outlier`-t kap, az `icpart1` kódolása a PLANNING_LOG-ban

## 4. Konfigurációk generálása

- [x] 4.1 `config/ess/common_core.json` (skálák, változók, közös szabályok); ellenőrzés: önállóan betölthető a `load_rules`-szal
- [x] 4.2 `config/ess/rN_core.json` N = 1, 3–11 (változó összetételű core skálák legalább 3 itemmel, kör-specifikus változók és szabályok); ellenőrzés: minden oszlop létezik a kör fájljában, `module` `core`, `required` `true`
- [x] 4.3 Rotáló modulok `config/ess/rN_<téma>.json` a blokktérkép szerint; ellenőrzés: `module` `rotating`, `required` `false`, alpha 0.01, min_items 5, min_rows_per_item 10 mindenhol
- [x] 4.4 Gyökérfájlok `config/ess1.json`, `config/ess3.json`–`config/ess11.json` az include-sorrenddel, a saját `essround` értékkel, az ESS2 gyökérbeállításaival és az Y−36/Y−54 életkorszabályokkal; ellenőrzés: mind a 10 betölthető, az `essround` megegyezik a fájlnév számával, és a képlet az ESS2-re 1969-et és 1951-et ad

## 5. GUI természetes sorrend

- [x] 5.1 `app.py` `bundled_rules_files()`: természetes rendezési kulcs a D8 szerint; ellenőrzés: a `tests/test_app_modular.py:34` elvárt listája a 13 fájlos `ess1 … ess11, scale_logic, spike_logic` sorrend, és zöld
- [x] 5.2 AppTest: a „Bundled rules file” választó pontosan ebben a sorrendben kínálja a fájlokat, `config/ess/` fájl nélkül; ellenőrzés: `pytest tests/test_app_modular.py -q` zöld

## 6. Tömeges validáció és teljes tesztfutás

- [x] 6.1 `tests/test_all_configs.py` a D7 szerint (glob-alapú parametrizálás, betöltés, include-útvonalak, skálanév-regex, includable kulcsok, árva modulok, `essround` = N, szintetikus futás körönként `essround` oszloppal, kimaradt core skála nélkül); ellenőrzés: zöld, és szándékos piros futás három rontással (hiányzó include, szóközös skálanév, árva modul), amelyek a fájlt megnevezve buknak, majd visszaállítás
- [x] 6.2 Teljes tesztfutás; ellenőrzés: `pytest -q` zöld, legalább 171 + az új tesztek száma, és a korábbi tesztek várt pontozási eredményei változatlanok

## 7. Valós próbafutás és GUI-ellenőrzés

- [x] 7.1 CLI-futás mind a 11 valódi fájlon a saját `config/essN.json`-jával, a kimenetek a scratchpadbe; ellenőrzés: nincs strukturális hiba, nincs kimaradt core skála, nincs „insufficient rows” core skála; körönként a PLANNING_LOG-ba: skálák száma, Mahalanobis-skálák száma, válaszadók, gyanúsak száma és aránya, straightlining, ellentmondás, Mahalanobis-jelöltek száma és aránya, az ESS2 viszonyítási sorával (22 skála, 1498 / 10 / 0,67% / 81 / 24 / 65 / 4,3%)
- [x] 7.2 Az ESS2 valódi futása a módosított `config/ess2.json`-nal; ellenőrzés: 1498 / 10 / 160 / 81 / 24 / 65 / 1498 / 0 / 96.22 / 33.33, és a pontozott CSV hash-e egyezik az 1.3-as értékkel
- [x] 7.3 Rossz kör próbája: az ESS4 valódi fájl a `config/ess3.json`-nal; ellenőrzés: a CLI `Rules file expects ESS round 3, but the data contains essround 4` hibával és 1-es kilépési kóddal áll le
- [x] 7.4 Vészjelzés a D11 szerint: minden olyan körre, ahol a gyanúsak aránya 2% fölött vagy a Mahalanobis-jelöltek aránya 8% fölött van, egy külön döntésre szánt sor a PLANNING_LOG-ba a kör számaival (a konfiguráció nem változik); ellenőrzés: a 7.1 számaiból minden ilyen körnek van sora, vagy egy sor rögzíti, hogy egyik kör sem lépte át a határt
- [x] 7.5 Kézi böngészős ellenőrzés a felhasználónak: a GUI „Bundled rules file” listája természetes sorrendben mutatja mind a 11 kört, egy kör futtatható, rossz kör választásakor a hibaüzenet megjelenik; ellenőrzés: a felhasználó visszajelzése

## 8. Dokumentáció és lezárás

- [x] 8.1 `README.md`: a beépített körkonfigurációk, az `essround` kulcs és hibái, az `ess_sav_files/` adatvédelmi szabálya; ellenőrzés: a leírt parancsok lefutnak
- [x] 8.2 `openspec validate add-ess-round-configs --strict` sikeres, a scratchpad valódi adatból készült kimenetei törölve, a `git status` szerint nincs `.sav`, scratchpad-szkript vagy metaadat-kivonat a repóban
