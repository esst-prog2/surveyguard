## Context

Lásd: proposal.md – Why. A tervhez szükséges, csak olvasva ellenőrzött tények (scratchpad-szkriptek, `pyreadstat.read_sav(..., metadataonly=True)`; a válaszadói értékekből csak összesítők):

- **A fájlok:** `ess_sav_files/ESS{1..11}_HU_weighted_raw.sav`, mérete 1,6–3,0 MB.

  | Kör | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
  |---|---|---|---|---|---|---|---|---|---|---|---|
  | Sorok | 1685 | 1498 | 1518 | 1544 | 1561 | 2014 | 1698 | 1614 | 1661 | 1849 | 2118 |
  | Oszlopok | 566 | 604 | 519 | 673 | 674 | 626 | 601 | 536 | 557 | 618 | 640 |
  | Terepév (Y) | 2002 | 2005 | 2007 | 2009 | 2010 | 2013 | 2015 | 2017 | 2019 | 2021 | 2023 |

  Y az `agea + yrbrn` legnagyobb értéke az érvényes sorokon. Az `agea` számított változó, így ez pontos (az ESS3-ban és az ESS6-ban a terepmunka két évre nyúlik át, ott a medián Y−1).
- **`essround`:** mind a 11 fájlban van ilyen oszlop. Hiányzó érték nincs benne, és csak a saját kör számát tartalmazza, lebegőpontosként (`float64`: 1.0 … 11.0).
- **Hiánykódok:** a `_raw` fájlok egyetlen oszlopra sem deklarálnak user-missing értéket vagy tartományt. A hiánykódok csak value labelként szerepelnek (`Refusal`, `Don't know`, `No answer`, `Not applicable`, `Not available`; pl. 77/88/99, 7/8/9, 66, 999, 7777/8888/9999). Így a `pd.read_spss` ezeket számként olvassa be, és a konfigurációban explicit `missing_codes` kell hozzájuk.
- **A `core.json` csak az ESS2-re illik** (jelenlét körönként, 1→11):
  - `trstprt`: `.XXXXXXXXXX`;
  - `prtyban`, `scnsenv`: `XXXXX......`;
  - `wkdcorga`, `iorgact`: `.XXXXXXXXXX`;
  - `wkdcpce`, `icptn`: `.X..X......`;
  - `partner`: `XXXX.......`;
  - `chldhm`: `XXXXXXXX...`;
  - `rshipa2`–`rshipa6`: `.XXXXXXXXXX`;
  - a 21 emberiérték-item: `XXXXXXXXXX.` (az ESS11-ben `ipcrtiva`, `impricha`, … néven).

  A `required: true` miatt a változatlan beemelés minden más körben strukturális hibát adna.
- **A HU fájlok más országok oszlopait is tartalmazzák** (pl. `edlvdat`, `prtvalt*`, `edlvpdie`). Az oszlop jelenléte tehát nem jelenti, hogy van benne magyar adat.
- **GUI:** `app.py:37-39` `sorted(CONFIG_DIR.glob("*.json"))`, csak a felső szint, lexikografikus sorrendben. A `tests/test_app_modular.py:34` a pontos listát rögzíti (`["ess2.json", "scale_logic.json", "spike_logic.json"]`).
- **Betöltő és bemenet:**
  - `surveyguard/config.py`: `ROOT_ONLY_KEYS = ("weights", "flag_threshold", "mahalanobis_min_scales", "id_column")`, `SCALE_NAME_PATTERN = ^[A-Za-z0-9_]+$`;
  - `surveyguard/io.py`: a `load_input` beolvasás után a `resolve_rules(rules, frame.columns)`-szal ellenőrzi az oszlopokat, és `DataValidationError`-t dob;
  - a CLI (`cli.py:33`) és a GUI (`app.py:227`) ugyanazt a `SurveyGuardError` ágat használja;
  - a `score_run` csak az oszlopneveket látja, értékeket nem.
- **ESS2 tesztbemenetek:**
  - a `tests/fixtures/ess2_mock.csv` (284 sor) nem tartalmaz `essround` oszlopot, és a repóban egyetlen fájl sem említi az `essround`-ot;
  - az ESS2-tesztek (`test_modular.py` `test_ess2_*`, `test_app_modular.py`, a `test_fast_scoring.py` ESS2-esete) mind ezt a fixture-t olvassák, vagy oszlopok elhagyásával belőle képeznek bemenetet;
  - egyik sem rögzíti a kimenet pontos oszloplistáját.
- **ESS2 viszonyítási pont a valódi fájlon** (`config/ess2.json`, 22 skála): 1498 válaszadó, 10 gyanús (0,67%), 160, 81 straightlining, 24 ellentmondás, 65 Mahalanobis-jelölt (4,3%), 1498, 0, 96.22, 33.33.

## Goals / Non-Goals

**Goals:**
- Minden kör a saját valódi fájlján strukturális hiba nélkül fut, a core skálák nem maradnak ki.
- Rossz kör választása (fájl és konfiguráció eltérése) a betöltéskor hibát ad, a CLI-ban és a GUI-ban is.
- A GUI a 11 kört természetes sorrendben kínálja fel.
- A konfigurációk reprodukálhatóan levezethetők a metaadatokból. A levezetési szabályok itt vannak leírva, a szkript nincs a repóban.
- Az ESS2 pontozási eredményei és a meglévő tesztek várt pontozási eredményei változatlanok.

**Non-Goals:**
- A `surveyguard/` csomag csak a `config.py` (az `essround` kulcs) és az `io.py` (az ellenőrzés a `load_input`-ban) érintett részén változik. A detektorok, a pontozás, a riport és a CLI-összefoglaló formátuma nem változik.
- Az `app.py`-ban csak a beépített fájlok rendezése változik.
- Nem állítjuk a körök közti összehasonlíthatóságot, és nem harmonizálunk változókat. Minden kör a saját kódkönyve szerint áll.
- Nem hangoljuk körönként a `flag_threshold` és a `mahalanobis_min_scales` értékét. Mindkettő az ESS2 értékét veszi át, a vészjelzés (D11) csak külön döntést kér.
- Az `essround` ellenőrzése nem fut, ha a hívó a `load_input` nélkül, közvetlenül a `score_run`-nak ad keretet (Python API). Ez ugyanígy van a meglévő oszlopellenőrzésnél is.
- A szkript, a metaadat-kivonatok és a valódi adatból készült kimenetek nem kerülnek a repóba.

## Decisions

### D1. Fájlszerkezet: közös core plusz körönkénti core, az ESS2 csak az `essround` kulccsal változik (a felhasználó döntése)

```
config/ess2.json   (+ "essround": 2)  → ess/core.json + ess/r2_*.json   (változatlan)
config/essN.json   (N = 1, 3..11)    → ess/common_core.json
                                       ess/rN_core.json
                                       ess/rN_<téma>.json …
```

- A `common_core.json` csak azt tartalmazza, ami mind a 11 körben azonos oszlopokkal megvan:
  - skálák: `Social_Trust`, `Satisfaction` (6 item), `Immigration_Policy` (`imsmetn`, `imdfetn`, `impcntr`), `Immigration_Effects`;
  - változók: `agea`, `yrbrn`, `hhmmb`, `gndr2`;
  - szabályok, amelyek csak ezekre hivatkoznak: `stfgov`/`stfdem`, `hhmmb`/`gndr2`.
- **Körről körre változó összetételű core skálák:** az `rN_core.json` definiálja őket, az adott kör összes elérhető itemével. Egy skála nem lehet „közös rész + körös kiegészítés”, mert egy oszlop csak egy skálában szerepelhet.
- **Legalább 3 item minden skálában** (a D4 küszöbe a core skálákra is vonatkozik). Egy core skála kimarad abból a körből, ahol 3-nál kevesebb iteme van, és az itemei csak akkor lesznek rule-only változók, ha egy szabály hivatkozik rájuk:
  - `Trust_Institutions`: 6 item az R1-ben, 7 az R2–11-ben;
  - `Policy_Attitudes`: 8 item az R1-ben (`ginveco` … `scnsenv`), 4 az R3–R5-ben, 5 az R8-ban (`gincdif`, `mnrgtjb`, `freehms`, `hmsfmlsh`, `hmsacld`), 4 az R9–R11-ben (`gincdif`, `freehms`, `hmsfmlsh`, `hmsacld`); az R6–R7-ben csak `gincdif` és `freehms` van, ezért ott kimarad (szabály nem használja őket, így változóként sem jelennek meg). A tervezéskor „R6–11” szerepelt itt; az alkalmazáskor az adat szerint javítva;
  - `Political_Efficacy`: 5 item az R1-ben (`polcmpl` … `pltinvt`), 6 az R7-ben (`psppsgv` … `etapapl`), 4 az R8–R11-ben (`psppsgva`, `actrolga`, `psppipla`, `cptppola`);
  - `Job_Autonomy`: 3 item csak az R5-ben (`wkdcorga`, `iorgact`, `wkdcpce`); az R3, R4, R6–11-ben 2 item van, ezért ott kimarad, és az R1-ben nincs;
  - `Human_Values`: 21 item az R1, R3–R10-ben, az R11-ben a tényleges `…a` nevekkel.
- A skálanevek a `core.json` neveit követik, hogy a riportok összevethetők legyenek. A `core.json` és a `common_core.json` sosem töltődik be együtt.
- **ESS2:** a `config/ess2.json` megkapja az `"essround": 2` kulcsot (a felhasználó döntése, D10). A `core.json` és az `r2_*.json` bájtra azonos marad.
- **Elvetett alternatívák:** a `core.json` szűkítése (megváltoztatná az ESS2 skálasorrendjét és a kimeneti oszlopokat); teljesen körönkénti core (a közös rész tízszer ismétlődne); 2 itemes core skálák (a D4 küszöbe alatt vannak, straightlining nem fut rajtuk, a Mahalanobis pedig 2 itemen kevés információt ad).

### D2. A metaadat-kinyerés és a generálás csak a scratchpadben fut (a felhasználó döntése)

- A szkriptek a scratchpadben vannak, és paraméterként kapják az `ess_sav_files/` útvonalát. A repóba nem kerül szkript, metaadat-kivonat vagy válaszadói érték.
- A kimenet a végleges JSON-fájlokat közvetlenül a `config/` mappába írja. Ezeket kézi átnézés után a tesztek és egy valós próbafutás ellenőrzi.
- **Elvetett alternatíva:** a generátor a repóban. A felhasználó kifejezetten csak a kimenetet kérte a repóba. A reprodukálhatóságot ez a dokumentum és a PLANNING_LOG biztosítja.

### D3. Tartományok és hiánykódok value labelekből

- A `missing_codes` a skála oszlopain a hiány-labelű kódok uniója (lásd a spec „Derive ESS missing codes…” követelményét).
- A `valid_min` és a `valid_max` a tartalmi kódok minimuma és maximuma. Egy skálába csak azonos tartalmi tartományú oszlopok kerülhetnek.
- A betöltő validációja (a missing kód a tartományon kívül) ezt automatikusan ellenőrzi.
- **Elvetett alternatíva:** az SPSS missing metaadat, mert ezekben a fájlokban üres.

### D4. Blokkképzés: automatikus jelöltek, kézi szociológiai csoportosítás, automatikus ellenőrzés

1. **Jelöltek:** a fájl oszlopsorrendjében egymás után következő, azonos sémájú (tartalmi tartomány és hiánykódok) itemek, legalább 3 egymás után. A tartomány legalább 4 pontos. A próbafutás körönként 19–43 jelöltblokkot és 133–223 itemet talált.
2. **Szűrés:**
   - országspecifikus oszlopok (label „, <ország>” vagy ország utótag, illetve 0 nem hiányzó magyar érték);
   - pártszavazat és -azonosulás (`prtv*`, `prtcl*`), háztartási tábla (`rshipa*`, `gndr*`, `yrbrn*`), végzettség (`edlv*`, `edu*`);
   - viselkedés- és gyakoriságblokkok, valamint olyan blokkok, ahol a nem hiányzó magyar sorok aránya 50% alatti.
3. **Kézi csoportosítás:** a jelölteket a scratchpad-generátorban egy körönkénti, kézzel írt blokktérkép (`skálanév → oszlopok`) bontja és nevezi el tematikusan. Ez választja szét az egymás mellé került, tartalmilag különböző itemeket (pl. `lrscale` és `stf*`; `happy` és `imwbcnt`). A fájlnév a rotáló modulok ESS-témáiból képzett `rN_<téma>.json`, az ESS2 téma-felbontása a minta.
4. **Automatikus ellenőrzés generáláskor:**
   - minden oszlop létezik a kör fájljában;
   - egy oszlop legfeljebb egy skálában vagy változóban szerepel;
   - minden skálának legalább 3 iteme és egységes tartománya van;
   - a `load_rules` hiba nélkül fut.

**Elvetett alternatíva:** tisztán automatikus csoportosítás. A próbafutás szerint a szomszédos, eltérő témájú itemeket összevonná.

### D5. Detektorok skálánként

- Alapértelmezés szerint mindkét detektor fut.
- Ha a skála valós magyar straightlining-aránya (teljes sorok közt, legalább 5 item) 5% felett van, csak `["mahalanobis_outlier"]` fut. Ez az ESS2 felhasználói kritériuma, összesítőként számolva.
- Az 5 itemnél rövidebb skálákon a `min_items_straightlining: 5` miatt amúgy sem fut straightlining.

### D6. Ellentmondás-szabályok

- A családokat és a küszöböket a spec „Generate round-specific contradiction rules” követelménye adja.
- **A partner- és gyerekváltozók körönként:**
  - R1–4: `partner`;
  - R2 és R5: `icptn`;
  - R5–8: `icpart1` (a kódolást az alkalmazáskor a value labelekből ellenőrizzük);
  - R1–8: `chldhm`;
  - R9–11: ezek a szabályok kimaradnak.
- A háztartási tábla szabályai az ESS2-höz igazodva `rshipa2`–`rshipa6`-ra szólnak.
- **Életkor/születési év:** a gyökérfájlban `agea <= 30 ∧ yrbrn <= Y−36` és `agea >= 60 ∧ yrbrn >= Y−54`. Az ESS2-re (Y = 2005) ez a meglévő 1969-et és 1951-et adja vissza.
- Minden szabály abba a fájlba kerül, amely minden oszlopát definiálja. A több fájl oszlopait használó szabály (pl. `partner == 1 ∧ hhmmb == 1`: `partner` az `rN_core.json`-ban, `hhmmb` a `common_core.json`-ban) a gyökérfájlba kerül, az életkorszabályokkal együtt.
- A rotáló modulok csak akkor kapnak saját szabályt, ha a blokkban egyértelmű logikai ellentétpár van (az `r2_health` `dckptrt`/`dcadmms` mintájára).

### D7. Tömeges validációs teszt (`tests/test_all_configs.py`)

- A `pytest.mark.parametrize` a `config/**/*.json` glob eredményén fut, keményen kódolt lista nélkül.
- **Ellenőrzések:**
  - a gyökérfájlok betöltése a `load_rules`-szal;
  - minden `include` relatív, `/`-t használ, nem lép ki a `config/` mappából, és létező fájlra mutat;
  - a skálanevek a regexre illeszkednek (a nyers JSON-ból, így a hibaüzenet a fájlt nevezi meg);
  - az almappák fájljai csak includable kulcsokat tartalmaznak;
  - nincs árva modul;
  - minden `essN.json` `essround`-ja N;
  - minden `essN.json` sikeresen fut egy szintetikus kereten, amelyet a konfigurációból építünk (determinisztikus seed, minden oszlop a tartományán belül, `essround` oszlop N értékkel). Közben ellenőrizzük, hogy kimaradt core skála nincs.
- A teszt nem olvas `.sav` fájlt.

### D8. GUI: természetes sorrend

- Az `app.py` `bundled_rules_files()` függvénye `sorted(CONFIG_DIR.glob("*.json"), key=...)`-ra vált. A kulcs a fájlnevet számjegyes és nem számjegyes darabokra bontja (`re.split(r"(\d+)", name)`); a számjegyes darabok egészként, a többi kisbetűsítve hasonlít.
- **Eredmény:** `ess1.json, ess2.json, …, ess11.json, scale_logic.json, spike_logic.json`.
- A `tests/test_app_modular.py:34` elvárt listája erre a 13 fájlos, természetes sorrendű listára frissül.
- Egy AppTest ellenőrzi, hogy a „Bundled rules file” választó pontosan ebben a sorrendben kínálja a fájlokat, `config/ess/` fájl nélkül.
- A fast-scoring követelmény szűkítése (spec MODIFIED delta) marad, mert a tesztlista és az ESS2 fixture így is változik.
- **Elvetett alternatíva:** átnevezés `ess01.json`… formára. Ez a felhasználó által kért `ess1.json` neveket és az ESS2 meglévő nevét is megváltoztatná.

### D9. `.gitignore`

- Új sorok: `ess_sav_files/` és `*.sav`, a megvalósítás első lépéseként.
- A meglévő tesztek `.sav` fájlt csak `tmp_path`-ba írnak, és a repó nem követ `.sav` fájlt.

### D10. `essround` körellenőrzés

- **`config.py`:**
  - `"essround"` bekerül a `ROOT_ONLY_KEYS`-be, így beemelt fájlban a meglévő hibaüzenet jön („'essround' may only be set in the root rules file, not in included file …”);
  - a `RulesConfig` új mezőt kap: `essround: int | None = None`;
  - a `load_rules` a meglévő `_positive_int`-tel validálja („essround must be a positive integer”), ami a `0`-t, a `"3"`-at, a `2.5`-öt és a `true`-t is elutasítja.
- **`io.py`:**
  - új `_check_essround(frame, rules)` segédfüggvény, amelyet a `load_input` közvetlenül a `resolve_rules(rules, frame.columns)` után hív (ugyanott, ahol a hiányzó oszlopok ellenőrzése fut). A `resolve_rules` csak oszlopneveket kap, ezért az értékellenőrzés nem fér bele;
  - **hibák** (`DataValidationError`):
    - nincs oszlop: `Rules file expects ESS round 3, but the data has no essround column`;
    - csak hiányzó értékek: `Rules file expects ESS round 3, but the data contains no essround value`;
    - eltérés: `Rules file expects ESS round 3, but the data contains essround 4` (több talált kör esetén vesszővel, növekvő sorrendben);
  - **összehasonlítás:** `pd.to_numeric(..., errors="coerce")` után számként (az SPSS 2.0-ja egyezik a 2-vel). A nem számként olvasható, nem üres érték is eltérésnek számít, és az eredeti szövegével jelenik meg. Az egész értékek tizedes nélkül jelennek meg a hibaüzenetben;
  - a hibát a CLI és a GUI a meglévő `SurveyGuardError` ágon mutatja, nincs új kezelés.
- **A csak üres oszlop esete** a felhasználó leírásán túli kiegészítés (Claude döntése): ellenőrzés nélkül átengedni azt jelentené, hogy a védelem csendben kikapcsol.
- **ESS2, (b) változat (a felhasználó döntése):**
  - a `config/ess2.json` megkapja az `"essround": 2`-t;
  - a `tests/fixtures/ess2_mock.csv` új, utolsó `essround` oszlopot kap, minden sorban `2` értékkel. Ez nem kérdés- és nem szabályoszlop, így a pontozott CSV-be változatlanul átmegy, a pontszámok, okok, kihagyott skálák és szabályok nem változnak;
  - a `test_fast_scoring.py` ESS2-esete ugyanazt a bemenetet adja a referenciának és az új kódnak, így továbbra is egyezik;
  - a `test_ess2_configuration_loads_with_documented_settings` kiegészül az `assert rules.essround == 2` sorral;
  - a valódi ESS2 fájlban már van `essround = 2`, ezért ott az eredmény változatlan: 1498 / 10 / 160 / 81 / 24 / 65 / 1498 / 0 / 96.22 / 33.33.
  - **Elvetett változat:** (a) `ess2.json` kulcs nélkül. Bájtra azonos maradna, de az ESS2 lenne az egyetlen ellenőrizetlen kör.
- **Új tesztek** (`tests/test_all_configs.py` mellett egy külön `tests/test_essround.py`): egyező kör, eltérő kör (pontos üzenet), hiányzó oszlop, csak üres oszlop, kulcs nélküli konfig (az `essround` oszlopot nem nézi), `essround` beemelt fájlban, érvénytelen értékek (`0`, `"3"`, `2.5`), SPSS-ből jövő `2.0` egyezése, valamint egy AppTest a rossz körre a GUI-ban.

### D11. Körönkénti vészjelzés

- **A valós próbafutás összesítője körönként:** skálák száma, Mahalanobis-skálák száma, válaszadók, gyanúsak száma és aránya, straightlining, ellentmondás, Mahalanobis-jelöltek (`mahalanobis_outlier_triggered`) száma és aránya.
- **Viszonyítási sor:** ESS2: 22 skála, 1498 válaszadó, 10 gyanús (0,67%), 81 straightlining, 24 ellentmondás, 65 Mahalanobis-jelölt (4,3%).
- **Vészjelzés:** ha egy körben a gyanúsak aránya 2% fölött vagy a Mahalanobis-jelöltek aránya 8% fölött van, külön döntésre szánt sor kerül a PLANNING_LOG-ba a kör számaival (a felhasználó döntése).
- A konfiguráció ebben a változásban nem hangolódik. Indok: az `mahalanobis_min_scales` 3 az ESS2 22 skálájához lett beállítva, a skálák száma viszont körönként eltér, ezért a hangolás külön döntés.

## Risks / Trade-offs

- [A kézi blokktérkép szubjektív] → Az ESS-modultémák és a kódkönyv-labelek a viszonyítási pontok. Minden skála labeljei bekerülnek a scratchpad-áttekintésbe, a tesztek a szerkezetet ellenőrzik.
- [A generátor nincs a repóban, a JSON-ok kézzel nem újragenerálhatók] → A D3–D6 levezetési szabályok, valamint a PLANNING_LOG darabszámai és hash-ei rögzítik az eredményt.
- [Országspecifikus vagy üres oszlop kerül egy skálába, ezért a Mahalanobis sosem fut] → A generálás szűri a nem hiányzó magyar értékek arányát. A valós próbafutás skálatáblázatában egy core skála sem lehet „insufficient rows”.
- [A skálák száma körönként eltér a 22-től, így az `mahalanobis_min_scales` 3 körönként lazább vagy szigorúbb lehet, és több gyanús jelölés jöhet] → D11: körönkénti összesítő az ESS2-sorral összevetve; 2% feletti gyanús- vagy 8% feletti Mahalanobis-arány esetén külön döntésre szánt sor a PLANNING_LOG-ban; a hangolás nem ebben a változásban történik.
- [Egy körtől eltérő, de hasonló oszlopszerkezetű fájl más konfigurációval csendben fut] → D10: `essround` ellenőrzés minden ESS gyökérfájlban, az ESS2-ben is.
- [Saját, `essround` oszlop nélküli ESS-kivonat a beépített `essN.json`-nal nem fut] → A hibaüzenet megnevezi a hiányzó oszlopot. Feltöltött, kulcs nélküli rules fájllal vagy egy `essround` oszlop hozzáadásával továbbra is futtatható. A README ezt leírja.
- [Az ESS2 fixture módosul] → Csak egy új, át nem alakított oszlop. A pontozási eredmények egyezését a meglévő ESS2-tesztek és a fast-scoring referencia ellenőrzi.
- [A 2 itemes core skálák kihagyása miatt a `gincdif`/`freehms` és a `wkdcorga`/`iorgact` egyes körökben semmilyen detektorba nem kerül] → Tudatos: 2 itemen egyik detektor sem ad érdemi jelet. Ha később szabály kell rájuk, változóként felvehetők.

## Migration Plan

- A meglévő konfigurációk közül csak a `config/ess2.json` kap új kulcsot. A kulcs nélküli (feltöltött vagy saját) rules fájlok viselkedése nem változik.
- A kódváltozás visszafelé kompatibilis: az `essround` opcionális.
- Visszaállításhoz elég az új fájlokat, a két `.gitignore` sort, az `essround` kulcsot és ellenőrzést, a fixture oszlopát, a rendezési kulcsot és a teszt lista-elvárását visszavonni.

## Open Questions

- Az `icpart1` pontos kódolása (1 = együtt él, 2 = nem) az R5–8-ban az alkalmazáskor, a value labelekből ellenőrizendő. Ez csak a szabály értékét érinti, a szabálycsaládot és a feladatokat nem.
