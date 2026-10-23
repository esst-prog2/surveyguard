## Context

A motivációt lásd a proposal.md „Why” részében. Jelenlegi állapot:

- `surveyguard/config.py`: `BlockConfig` (`min`, `max`, `missing_values`, `high_min`, `low_max`, `irv_threshold`), `PairConfig` (fordított pár), `RulesConfig` (`blocks`, `inverted_pairs`, `weights`, `thresholds`, `flag_threshold`, `id_column`). A Mahalanobis-küszöb egyetlen globális érték: `thresholds.mahalanobis_outlier`.
- `surveyguard/scoring.py` `_normalise_questions`: blokkonként NaN-ná maszkolja a hiánykódokat és a tartományon kívüli értékeket. A detektorok erre a maszkolt keretre futnak, a nyers értékek a kimenetben maradnak. Ez a cellaszintű hiánykezelés már most megfelel a kérésnek, ezért csak a mezőnevek változnak.
- `surveyguard/detectors.py`: a `straightlining` már blokkonként fut (`Straightlining_Error:<blokk>`). A `mahalanobis(rows, columns, threshold)` egyetlen hívással az **összes** kérdésoszlopon számol. A `logical_contradictions` a fordított párokat high/low sávokkal értékeli.
- A `reporting.py`, a `cli.py` és az `app.py` csak a `*_triggered`, `*_available`, `quality_score`, `suspicious`, `flag_reasons` és `data_quality` oszlopokat használja. A `mahalanobis_distance` oszlopot csak a `tests/test_core.py` olvassa.
- `run_spike.py`: kézzel épít `BlockConfig`/`PairConfig` objektumot, és meghívja a három detektorfüggvényt.
- Alapállapot: 67 zöld teszt (`python -m pytest -q`). A spike-baseline mérését lásd a `spike-tooling` delta két követelményében: a CLI-összesítő a régi `config/scale_logic.json`-nal, és a `run_spike.py` kimenete.
- A felhasználó döntései (2026-10-23): a spike-konfig átköltözik, nincs visszafelé kompatibilitás, a hiánykódokat cellaszinten ignoráljuk, az okcímkében a skála neve szó szerint szerepel.

## Goals / Non-Goals

**Goals:**
- Egy szabálymodell (`scales` + `contradictions`) szolgálja ki az ESS-t és a spike-ot is, külön kódág nélkül.
- A detektorok, a súlyok és a kimeneti oszlopok neve marad. Így a `reporting.py`, a `cli.py` és az `app.py` kódja nem változik, és a CLI–GUI egyenértékűségi tesztek változatlan logikával futnak tovább.
- A spike-számok (50 kalibrált outlier, a CLI-összesítő, a `run_spike.py` kimenete) bitre azonosak maradnak.

**Non-Goals:**
- A régi séma átfordítása vagy két séma párhuzamos támogatása.
- Skálánkénti súlyok vagy skálánkénti pontszám. A detektor-penalty továbbra is 0/1, és az aggregálás képlete nem változik.
- VAGY-kapcsolat, negálás vagy oszlop–oszlop összehasonlítás az ellentmondásszabályokban. Csak az oszlop–konstans feltételek ÉS-kapcsolata támogatott.
- Valódi ESS-adat letöltése vagy commitolása (adatvédelmi követelmény). Commitolt `.sav` fixture sem lesz: a `.sav` és `.xlsx` teszteket továbbra is a tesztek generálják ideiglenes fájlba.
- GUI-módosítás. A feltöltés, a táblák és a letöltések változatlanok.

## Decisions

1. **Új konfigurációs modell, a régi dataclassok törlődnek.**
   - `ScaleConfig(name, columns, valid_min, valid_max, missing_codes, irv_threshold, mahalanobis_threshold)`
   - `Condition(column, op, value)`
   - `ContradictionRule(conditions)`, `label` tulajdonsággal (`"Contradiction: " + " vs ".join(f"{c.column}{c.op}{c.value:g}")`)
   - `RulesConfig(scales, contradictions, weights, flag_threshold, id_column)`, megtartott `question_columns` tulajdonsággal, mert ezt az `io.py` használja.

   A `BlockConfig` és a `PairConfig` megszűnik, nem marad alias. A JSON-kulcsok a kérés szerintiek (`valid_min`, `valid_max`, `missing_codes`). A `:g` formátum a `8.0`-ból `8`-at, a `2.5`-ből `2.5`-öt ír, ez adja a specben előírt „egész szám tizedes nélkül” alakot.
   *Alternatíva:* a régi nevek megtartása (`min`, `max`, `missing_values`). Elvetettük, mert a kérés kifejezetten az új neveket kéri, és a régi sémát úgysem támogatjuk tovább.

2. **A Mahalanobis-küszöb skálánkénti és kötelező.** A χ²-alapú küszöb a szabadságfoktól, vagyis a skála itemszámától függ (a 4 itemes és az 5 itemes skála küszöbe más), ezért egy globális érték két különböző hosszúságú skálára hibás lenne.
   - ESS-értékek: a χ² eloszlás 0,95-ös kvantilise (5 itemre `11.070498`, 4 itemre `9.487729`). Ez összhangban van a spike-ban elfogadott 5%-os téves riasztási szinttel.
   - Spike: a kalibrált `9.829530` megmarad.
   - A küszöb nem számolódik automatikusan (nincs `scipy`-függőség): a JSON-ban kell megadni.

   *Alternatíva:* globális küszöb skálánkénti felülírással. Elvetettük, mert két helyen lehetne ugyanazt állítani, és a hibás globális alapérték csendben rossz eredményt adna.

3. **A Mahalanobis skálánként fut, saját kovarianciával és saját érvényes sorhalmazzal.** A generikus `mahalanobis(rows, columns, threshold)` megmarad. A `score_dataframe` skálánként hívja, így egy hiányzó trust-item csak a trust-távolságot ejti ki, a satisfaction-távolságot nem.
   - A `MathematicalError` üzenete tartalmazza a skála nevét.
   - Kimenet: skálánként egy `mahalanobis_distance_<skála>` oszlop, a `detector_details` JSON-ban pedig `{"distances": {skála: érték}}`.
   - Az egyetlen `mahalanobis_distance` oszlop megszűnik.

   *Alternatíva:* a régi oszlop megtartása a skálák maximumával. Elvetettük, mert félrevezető: különböző küszöbű skálák távolságai nem összemérhetők.

4. **A régi séma explicit elutasítása.** A `load_rules` minden más ellenőrzés előtt megnézi a `blocks`, `inverted_pairs` és `thresholds` kulcsot, és `ConfigurationError`-t dob ezzel az üzenettel: `Legacy rules key 'blocks' is no longer supported; use 'scales' and 'contradictions'`. Így a felhasználó nem egy félrevezető „scales is required” hibát kap. A GUI ugyanezt az `Error:` üzenetet mutatja.

5. **Validációs szabályok** (mind `ConfigurationError`):
   - **Skálanév:** csak betű, szám és aláhúzás lehet (`^[A-Za-z0-9_]+$`), mert oszlopnévbe (`mahalanobis_distance_<név>`) és okcímkébe kerül, és nem tartalmazhat `;`-t, ami a `flag_reasons` elválasztója.
   - **Oszlopok:** egy oszlop legfeljebb egy skálában szerepelhet, különben a hiánykezelés és a Mahalanobis kétértelmű lenne.
   - **Hiánykódok:** nem eshetnek a `valid_min`–`valid_max` tartományba, mert érvényes választ maszkolnának.
   - **Ellentmondásszabályok:** legalább két feltétel; az `op` a `>`, `>=`, `<`, `<=`, `==` egyike; a `value` szám (bool nem); az oszlop valamelyik skálában szerepel. A hibaüzenet a szabályt az indexével azonosítja (`contradictions[1].conditions[0].op ...`).

6. **Az ellentmondás-detektor a maszkolt soron fut.** Egy szabály csak akkor értékelődik, ha minden oszlopa érvényes (nem NaN). Több szabály egyszerre is triggerelhet, ilyenkor mindegyik külön okot ad, konfigurációs sorrendben. A detektor neve (`logical_contradiction`) és oszlopai maradnak. A riportban és a GUI-ban a megjelenített név már ma is „Contradiction”.

7. **Okcímkék és sorrend.**
   - Straightlining: `Straightlining_<skála>`, skálasorrendben.
   - Ellentmondás: `Contradiction: ...`, szabálysorrendben.
   - Mahalanobis: `Mahalanobis_<skála>`, skálasorrendben.

   Ez a régi detektorsorrend. A `Contradiction: ...` címke szóközt és `>`/`<` jelet tartalmaz. Ez CSV-ben és Markdown-táblában is biztonságos: a `|`-t a riport már ma escape-eli, a `;` pedig nem fordulhat elő a címkében, mert a skálanevek validáltak, és a szabályok oszlopai skálaoszlopok.

8. **ESS-referenciakonfiguráció.** Az `id_column` értéke `idno`. A két skála a proposal szerinti; `irv_threshold` 0. Az ellentmondásszabályok:
   - `trstplt > 8` és `trstprl < 2` (a kérésből);
   - `trstprt > 8` és `trstplt < 2` (a pártokban nagyon bízik, a politikusokban egyáltalán nem);
   - `stfgov > 8` és `stfdem < 2` (a kormánnyal nagyon elégedett, a demokrácia működésével egyáltalán nem).

   A második és a harmadik szabály heurisztika. A JSON-ban szabadon hangolható, a tesztek csak az elsőre és a mechanizmusra építenek.

9. **Spike-konfiguráció és `run_spike.py`.** A `config/spike_logic.json` egy `Extraversion` skálát tartalmaz (`EXT1`–`EXT4`, 1–5, `mahalanobis_threshold` `9.829530`), és a régi `EXT2`/`EXT3` párt két szabályként: `EXT2>=4 vs EXT3>=4` és `EXT2<=2 vs EXT3<=2`. A `logical_contradiction` súlya 0. A két szabály egyszerre sosem teljesülhet, ezért a triggerelt válaszadók száma pontosan a régi páros detektoré (140), és a CLI-összesítő minden száma változatlan. A `run_spike.py` ugyanígy négy szabállyal fejezi ki az `EXT1`/`EXT2` és `EXT3`/`EXT4` párt, és az új dataclassokat építi. A kimenetét a baseline-hoz hasonlítjuk.

10. **Az `ess_mock.csv` kézzel tervezett, determinisztikus szintetikus fájl.** Kb. 30 sor, oszlopai `idno`, `cntry` (metaadat) és a 9 item. Kijelölt sorok:
    - egy-egy straightliner skálánként, és egy, amelyik mindkettőn az;
    - legalább egy sor mindhárom ellentmondásszabályhoz, és egy határeset (`trstplt` = 8);
    - 77, 88 és 99 hiánykód különböző skálákon;
    - egy `11`-es (tartományon kívüli) érték és egy nem numerikus érték;
    - szélsőséges, de érvényes válaszminta a Mahalanobis-hoz;
    - a többi „tiszta”, elég változatos sor, hogy mindkét kovarianciamátrix invertálható legyen.

    A pontos várt számokat (gyanús, skálánkénti triggerek, Mahalanobis-outlierek) az implementáció egyszer lefuttatja, kézzel ellenőrzi, majd a tesztekbe és a PLANNING_LOG-ba rögzíti. A sorokat nem generátorszkript állítja elő, hogy a fixture olvasható és auditálható maradjon.

11. **Teszt-migráció.**
    - A pipeline-, CLI-, riport- és GUI-tesztek a `config/scale_logic.json` + `tests/fixtures/ess_mock.csv` párost használják, a régi `survey.csv` és `rules.json` törlődik.
    - A validációs és alapértelmezés-tesztek kis, inline ESS-nevű JSON-t írnak `tmp_path`-ba.
    - A fordított párok sávlogikáját tesztelő esetek az ellentmondásszabályokra íródnak át (szigorú és nem szigorú határ, hiányzó érték), így a tesztszám nem csökken 67 alá.
    - A `test_real_world.py` a `config/spike_logic.json` skálaküszöbét olvassa.
    - A `test_spike_scripts.py` nem változik.
    - Új tesztek: régi séma elutasítása, a hiánykód a tartományban, duplikált oszlop, skálánkénti Mahalanobis (az egyik skála hiányos), szinguláris skála névvel, több okcímke egy soron, a `66.67`-es pontszám két straightlining-skálánál.

    *Alternatíva:* egy külön `tests/fixtures/ess_rules.json` a produkciós konfig helyett. Elvetettük, mert a kérés szerint a tesztek az új ESS-konfigurációt használják. A kockázatot lásd lent.

## Risks / Trade-offs

- [A régi sémájú szabályfájlok azonnal betölthetetlenek] → Az elutasító üzenet megnevezi a régi kulcsot és az új kulcsokat. A README migrációs bekezdést kap (fordított pár → két szabály), és a REMOVED követelmény migrációs leírása is ezt mondja.
- [A `flag_reasons` címkéinek változása eltöri a szöveges utófeldolgozást] → A változás BREAKING-ként szerepel a proposalban és a README-ben. A `*_triggered` oszlopok stabilak maradnak, gépi feldolgozáshoz ezeket ajánljuk.
- [A tesztek a produkciós `config/scale_logic.json`-hoz kötődnek, így a küszöbök későbbi hangolása tesztet törhet] → Ez szándékos (a tesztek a valódi konfigurációt védik). A mechanizmustesztek inline konfigot használnak, ezért hangoláskor csak a fixture-számokat rögzítő néhány teszt változik.
- [A χ² 0,95-ös küszöb normalitást feltételez, az ESS 0–10-es válaszai ferdék és diszkrétek, így valós adaton a téves riasztás aránya eltérhet az 5%-tól] → A küszöb skálánként hangolható. Valós ESS-mintán a `run_spike.py` kalibrációs módszere is alkalmazható. Ez nem része ennek a változásnak.
- [Kis fixture-ön a kovarianciamátrix szinguláris lehet] → A tiszta sorok kézzel változatosak. A fixture-t a tesztírás előtt egy egyszeri `score_dataframe`-futás ellenőrzi.
- [Az 5 itemes skála miatt a sorok több okot kaphatnak, így a GUI-ban és a riportban hosszabbak az okcellák] → Elfogadott. A cellák már ma is `;`-vel elválasztott listát mutatnak.

## Migration Plan

1. Kód és konfiguráció cseréje egy commitban a tesztekkel együtt, hogy a `main`-re soha ne kerüljön félig migrált állapot.
2. Ellenőrzés:
   - `python -m pytest -q` minden teszten zöld;
   - `python detect_anomalies.py spike_data.csv --rules config/spike_logic.json` a baseline-számokat adja;
   - a `python run_spike.py` kimenete azonos;
   - a CLI és a GUI ugyanazt a riportot adja az `ess_mock.csv`-n.
3. Visszaállítás: `git revert` a commitra. Adatmigráció nincs, a kimeneti fájlokat minden futás újragenerálja.
