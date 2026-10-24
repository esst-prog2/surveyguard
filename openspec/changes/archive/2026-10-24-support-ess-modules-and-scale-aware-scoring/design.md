## Context

A motivációt lásd a proposal.md „Why” részében. Jelenlegi állapot (`feat-ess-scales`, archivált change: `2026-10-23-support-ess-scales-and-contradictions`):

- **`surveyguard/config.py`:**
  - a `load_rules(path)` egyetlen JSON-t olvas;
  - `ScaleConfig` (`name`, `columns`, `valid_min`, `valid_max`, `missing_codes`, `irv_threshold`, `mahalanobis_threshold`), `Condition`, `ContradictionRule`, `RulesConfig` (`scales`, `contradictions`, `weights`, `flag_threshold`, `id_column`);
  - egy szabályfeltétel oszlopának skálában kell lennie.
- **`surveyguard/io.py`:** a `_validate_frame` minden skálaoszlopot kötelezőnek vesz. SPSS-nél a `pd.read_spss(..., convert_categoricals=False)` a deklarált user-missing kódokat (pl. 77/88/99, 7/8/9) üres értékként olvassa be. A missing tartományon kívüli, nem tartalmi kódok (pl. 6 = „No experience”, 8 = „Neither partner does paid work”) számként maradnak. Ezt az ESS2 fájlon ellenőriztük.
- **`surveyguard/detectors.py` és `scoring.py`:**
  - a straightlining és a Mahalanobis skálánként fut, de a büntetés 0/1 („bármelyik skálán jelez”);
  - a `mahalanobis(rows, columns, threshold)` 2 érvényes sor alatt NaN-t ad;
  - a `score_dataframe` csak a pontozott keretet adja vissza, a skálánkénti adatok csak a `flag_reasons`-ban és a `detector_details` JSON-ban vannak.
- **`surveyguard/reporting.py`:** a `render_report(frame, id_column)` és a `print_summary(frame, output_path)` csak a pontozott keretből dolgozik.
- **`app.py`:** a feltöltött rules fájlt egy ideiglenes mappába írja `rules.json` néven, így relatív include ott nem oldható fel.
- A **`run_spike.py`** kulcsszavas argumentumokkal építi a `ScaleConfig`/`RulesConfig`-ot, és a `straightlining(...).triggered`, `logical_contradictions(...).triggered`, `mahalanobis(...)` hívásokat használja.
- **Függőségek:** a SciPy egy korábbi audit óta nincs a `requirements.txt`-ben. Telepítve 1.17.1 van (Python 3.14.3).
- **Alapállapot:** 91 zöld teszt. Spike CLI: 1000 / 2 / 181 / 20 / 140 / 47 / 0 / 13 / 13 / 96.61 / 0.00. ess_mock CLI: 33 / 3 / 9 / 4 / 4 / 4 / 2 / 2 / 0 / 87.88 / 33.33.

## Goals / Non-Goals

**Goals:**
- A `load_rules` egy include-fát egyetlen, a mai értelemben érvényes `RulesConfig`-gá fésül össze. A detektorok és a pontozás így nem tudnak a fájlszerkezetről.
- Minden új mező alapértéke a mai viselkedést adja. A `config/spike_logic.json`, a `config/scale_logic.json` és a `run_spike.py` nem változik.
- A büntetés mindhárom detektornál 0/1 marad. A `mahalanobis_min_scales` alapértéke (1) pontosan a mai „bármelyik skálán” logika, ezért a spike és az ess_mock pontszámai, okai és pontozott CSV-je bájtra azonos.
- A skálánkénti adatok (küszöb, érvényes sorok, jelölések, státusz) egyetlen helyen keletkeznek, a pontozásban, és a riport, a CLI meg a GUI ugyanazt az objektumot olvassa.

**Non-Goals** (a kérés non-goal listáján túl):
- Skálánkénti súlyok vagy skálánkénti pontszám. A detektorsúlyok továbbra is detektorszintűek.
- Oszlop–oszlop vagy aritmetikai feltétel a szabályokban (pl. `agea + yrbrn`). A kor–születési év konzisztenciát sávszabályok fedik (D11).
- Skálánkénti alapértékek örökítése include-on át (pl. közös `scale_defaults`). Minden skála explicit, ami a JSON-ban ismétlést jelent, de egyértelmű.
- A felöltött GUI-rules fájl include-jainak feloldása (D9).

## Decisions

### D1. Include-feloldás és összefésülés

- A `load_rules(path, *, allow_include=True)` először rekurzívan betölti a fájlfát:
  - a `_load_tree(path, stack)` mélységi bejárással, listasorrendben adja vissza a `(fájl, adat)` párokat, előbb a beemelt fájlokat, utána a saját bejegyzéseket;
  - az útvonalakat a beemelő fájl mappájához képest oldja fel, `Path.resolve()`-val normalizálja, és a hibaüzenetekben a gyökérfájl mappájához viszonyított formában írja ki.
- **Körkörös include:** ha a feloldott fájl már a `stack`-ben van, a hiba a teljes láncot megnevezi (`a.json -> b.json -> a.json`).
- **Ismételt include:** ha egy fájl a láncon kívül másodszor fordul elő (gyémánt), az is hiba. Indok: az ismétlés skálanév-ütközést okozna, de egy „included more than once” üzenet közvetlenebb.
- **Kulcsok:** beemelt fájlban csak `include`, `scales`, `variables` és `contradictions` lehet. A `weights`, a `flag_threshold`, a `mahalanobis_min_scales` és az `id_column` csak a gyökérben állhat, máshol hiba a fájl nevével. A régi kulcsokat (`blocks`, `inverted_pairs`, `thresholds`) minden fájlban elutasítjuk, a fájl nevével.
- **Ütközések:** az összefésüléskor fájlonkénti tulajdonost tartunk nyilván (`{skála: fájl}`, `{oszlop: (skála vagy változó, fájl)}`). Ütközésnél a hiba mindkét fájlt és mindkét skálát vagy változót megnevezi. A szabályok a hibaüzenetben fájlonkénti pozícióval szerepelnek (`contradictions[2] in ess/r2_family_work.json`).
- Alternatíva volt egy előfeldolgozó lépés, amely a fájlokat egy JSON-ba írja ki. Elvetettük, mert két forrásigazságot hozna létre.

### D2. Rule-only `variables`

- A bináris, kategoriális, darabszám- és évszám-változók nem lehetnek skálák, a szabályokhoz viszont tartomány és missing kód kell nekik. Ezért kapnak saját szakaszt: `VariableConfig(name, valid_min, valid_max, missing_codes, module, required)`.
- A normalizálás (`_normalise_questions`) a változókat is maszkolja, így a szabály a mai logikával kihagyja a hiányzó vagy érvénytelen értéket.
- A változók nem kapnak `data_quality` jelölést. Indok: a háztartási tábla (`rshipa3`… `gndr6`…) és a szűrt blokkok 6/66-os kódjai szinte minden válaszadónál `Missing_Value`-t adnának, és ezzel a hiányzó-számláló értelmét vesztené.
- Alternatíva volt a feltételek oszlopait a szabályon belül típusozni (`{"column": "partner", "valid": [1, 2]}`). Elvetettük, mert ugyanaz a változó több szabályban ismétlődne.

### D3. Új skálamezők és alapértékek

A `ScaleConfig` új mezői a meglévők után következnek, alapértékkel, így a `run_spike.py` kulcsszavas konstruktorhívása nem változik:

- `module: str | None = None`;
- `required: bool = True`;
- `detectors: tuple[str, ...] = ("straightlining", "mahalanobis_outlier")`;
- `min_items_straightlining: int | None = None`;
- `mahalanobis_min_rows_per_item: float = 0`;
- `threshold_source: str = "configured"`.

A `mahalanobis_threshold` típusa `float | None` lesz: `None`, ha a skálán nincs Mahalanobis detektor.

A `RulesConfig` új gyökérszintű mezője `mahalanobis_min_scales: int = 1`: pozitív egész (`bool` nem fogadható el), beemelt fájlban hiba (D1).

Validáció:
- a `detectors` nem üres, ismétlés nélküli részhalmaza a két skála-detektornak;
- a `min_items_straightlining` pozitív egész;
- a `mahalanobis_min_rows_per_item` nem negatív szám;
- a `module` nem üres szöveg; a `"core"` és a `"rotating"` a dokumentált érték, de a kód nem szűkít rá, mert csak megjelenítésre szolgál.

### D4. Alpha alapú küszöb (`scipy.stats.chi2.ppf`)

- Betöltéskor a küszöb `chi2.ppf(1 - alpha, df=len(columns))`, a `threshold_source` értéke pedig `alpha=<alpha:g>`.
- A SciPy újra függőség: `scipy==1.15.3; python_version < "3.11"` és `scipy==1.17.1; python_version >= "3.11"` (a felhasználó döntése).
- Ellenőrzött referenciaértékek:
  - df 5 / alpha 0.05 → 11.070498, df 4 / alpha 0.05 → 9.487729 (megegyezik a `scale_logic.json` küszöbeivel);
  - df 4 / 0.01 → 13.276704, df 5 / 0.01 → 15.086272;
  - df 7 / 0.01 → 18.475307, df 21 / 0.01 → 38.932173.

### D5. Minimális érvényessor-szám

- A szükséges sorszám `max(2, ceil(mahalanobis_min_rows_per_item × itemszám))`. Az alapérték 0, így a mai „legalább 2 sor” marad (a felhasználó döntése).
- Ez alatt a `mahalanobis` nem számol: a skála oszlopa üres, státusza `not available (<n> valid rows, needs <m>)`, és nem kerül a nevezőbe.
- A szinguláris kovariancia továbbra is `MathematicalError` a skála nevével. A minimum ezt ritkítja, de nem helyettesíti.

### D6. 0/1 büntetés, m-küszöbös Mahalanobis és a futási metaadat

Az első tervváltozat arányos büntetést (jelző / értékelt skálák) javasolt. A valós ESS2 HU adaton ez felhígította az erős jeleket:
- egyetlen straightlining-skála 1/5–1/7 büntetést adott;
- a három Human_Values-straightliner (2051, 2084, 2307) 79–90 pontot kapott;
- a Mahalanobis-büntetés átlagosan 1/17-re hígult, és a szűrt blokkok miatt a kevés blokkot kitöltőket büntette jobban;
- 1498 főből 50 alatt senki nem maradt.

A felhasználó ezért 2026-10-24-én az alábbira cserélte (lásd Q12 és Q9):

- **Straightlining:** 0/1, értéke 1, ha bármelyik értékelhető skálán jelez. A `straightlining(row, scales)` csak az értékelhető skálákon fut: nincs kihagyva, a `detectors`-ban szerepel, az itemszám legalább `min_items_straightlining`, és a sor teljes. A téves riasztást a `min_items_straightlining` és a skálánkénti kikapcsolás kezeli (az értékelt ESS-skálákon 0–4,8%).
- **Mahalanobis:**
  - a `score_dataframe` skálánként megállapítja a jelzéseket (távolság > küszöb);
  - a detektor `triggered`, ha a jelző skálák száma ≥ `mahalanobis_min_scales` (m), és csak ekkor kerülnek a `Mahalanobis_<skála>` okok a `flag_reasons`-ba, konfigurációs sorrendben;
  - a büntetés 0/1;
  - a detektor elérhető, ha legalább egy skálán van távolság. Ha egy válaszadónál m-nél kevesebb skála értékelhető, a detektor elérhető, de nem jelölhető (lásd Risks).
- **Ellentmondás:** 0/1 marad (Q3).
- **Láthatóság m alatt:** a távolságoszlopok és a skálatáblázat változatlanul mutatják a skálaszintű jelzéseket. A `detector_details.mahalanobis_outlier` csak `m > 1` esetén kap egy `flagged_scales` listát. m = 1-nél a JSON nem változik, így a spike és az ess_mock pontozott CSV-je bájtra azonos marad; ilyenkor a jelzett skálák amúgy is mind okként szerepelnek.
- **Nincsenek új oszlopok:** a `*_penalty` oszlopok kikerültek a tervből, mert a 0/1 büntetést a `*_triggered` egyértelműen leírja.
- **Futási objektum** (változatlanul a tervben): `score_run(frame, rules) -> ScoringRun(scored, scales, skipped_scales, skipped_rules)`.
  - A `ScaleRun` mezői: `name`, `module`, `items`, `detectors`, `threshold`, `threshold_source`, `valid_rows`, `required_rows`, `straightlining_count`, `mahalanobis_count`, `mahalanobis_status`.
  - A `ScaleRun.mahalanobis_count` a skálaszintű jelzések száma (távolság > küszöb), attól függetlenül, hogy a válaszadó elérte-e az m-et. A detektortáblázat Mahalanobis-száma ezzel szemben az m-küszöböt elérő válaszadóké.
  - A `score_dataframe(frame, rules)` megmarad, és `score_run(...).scored`-ot ad vissza, így a meglévő tesztek és hívók nem változnak.
- Alternatíva volt a skálaadatokat a `DataFrame.attrs`-ba tenni. Elvetettük, mert a pandas-műveletek nem őrzik meg megbízhatóan.

### D7. Kihagyott skálák és szabályok (`io.resolve_rules`)

- A `resolve_rules(rules, columns) -> ResolvedRules(rules, skipped_scales, skipped_variables, skipped_rules)` dönti el a kimaradást:
  - a `required: true` skála vagy változó hiányzó oszlopa hiba (a mai üzenet);
  - a `required: false` skála, amelynek minden oszlopa hiányzik, kimarad;
  - ha egy ilyen skálának csak részben hiányoznak az oszlopai, az hiba (Q2);
  - a kihagyott oszlopra hivatkozó szabály kimarad;
  - ha minden skála kimarad, az hiba.
- A `load_input` a validáláshoz hívja, a `score_run` a tényleges aktív konfigurációhoz. Ez tiszta függvény, a kétszeri hívás olcsó.
- A kihagyott skála nem kap távolságoszlopot és `data_quality` jelölést.

### D8. Riport és CLI

- A `render_report(frame, id_column=None, run=None)` és a `write_report(..., run=None)` új szakaszt kap a „Detector results” után, ha a `run` meg van adva:
  - a „## Scale results” táblázat oszlopai: `Scale | Module | Items | Detectors | Threshold | Valid rows | Straightlining | Mahalanobis flags (scale-level) | Status`;
  - a „Detector results” táblázat alá egy sor kerül: `Mahalanobis counts respondents flagged on at least <m> scale(s).`;
  - a „## Skipped scales and rules” szakasz két listát tartalmaz, üres esetben `None`-nal.
- `run=None` esetén a riport bájtra a mostani. Így a meglévő, közvetlen `render_report`-golden teszt nem változik, a CLI és a GUI viszont mindig átadja a `run`-t.
- A `print_summary(frame, output_path, skipped_scales=())` a `Not scored reason` sor után csak nem üres listánál ír `Skipped scales: A, B` sort. A spike-összefoglaló így bájtra azonos (a felhasználó döntése).
- A táblázat adatait a `reporting.scale_results(run) -> DataFrame` adja, ezt használja a GUI is.

### D9. GUI

- A sidebar „Rules source” rádiógombot kap két opcióval: „Upload a rules file” (a mai feltöltő) és „Bundled rules file”. Utóbbi egy selectbox a `config/*.json` fájlokkal (csak a felső szint, rendezve: `config/ess2.json`, `config/scale_logic.json`, `config/spike_logic.json`).
- A `run_surveyguard(data_name, data_bytes, rules_bytes=None, *, rules_path=None)`:
  - beépített fájlnál a repóbeli útvonalon hívja a `load_rules`-t, így az include ugyanúgy oldódik fel, mint a CLI-ben;
  - feltöltött fájlnál `load_rules(..., allow_include=False)`, ami include esetén ezt a hibát adja: `include is not supported for uploaded rules files; choose a bundled rules file or use the command-line tool`.
- A `run_key` a forrást is tartalmazza (`("upload", file_id)` vagy `("bundled", path)`), így forrásváltásnál eltűnnek a régi eredmények.
- Az eredmények között a detektortáblázat mellett/alatt megjelenik a skálatáblázat (`st.dataframe`). Kihagyott skála vagy szabály esetén egy `st.info` nevesíti őket.
- A detektortáblázat és a diagram nem változik.
- Alternatívák voltak (a felhasználó elvetette őket): csak hibaüzenet, illetve több JSON feltöltése.

### D10. ESS2-konfiguráció (`config/ess2.json` + `config/ess/*.json`)

A kódokat a `.sav` metaadataiból (value labels, missing ranges) és a tényleges értékekből ellenőriztük, csak olvasva, a scratchpadből futó szkriptekkel. Közös beállítások: `mahalanobis_alpha` 0.01, `min_items_straightlining` 5, `mahalanobis_min_rows_per_item` 10 (a felhasználó döntése). A gyökér `config/ess2.json` beállításai: `id_column` `idno`, `flag_threshold` 50, `mahalanobis_min_scales` 3 (a felhasználó döntése). A core skálák `required: true`, a rotáló skálák `required: false`.

A missing kódok skálaszintű uniók. A rövid skálákon a 6 csak ott szerepel, ahol a .sav 6..9 tartományt deklarál, vagy ahol a 6 nem tartalmi válasz. A `Work_Family_Conflict` skálán a 6 („Don't have partner/family”) a missing tartományon kívül esik, ezért számként jön be, és explicit missing kódként kell kezelni.

A táblázat utolsó három oszlopa a valós ESS2 HU adaton mért érték:
- **Teljes:** a skálát teljesen kitöltő válaszadók száma;
- **SL%:** a mindenre azonos választ adók aránya közöttük;
- **MH (α 0.01):** a Mahalanobis-jelölések száma alpha 0,01 mellett.

| Fájl | Skála | Itemek | Tartomány | Missing kódok | Detektorok | Teljes | SL% | MH (α 0.01) |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| core | Social_Trust | ppltrst, pplfair, pplhlp | 0–10 | 77, 88, 99 | mindkettő (SL <5 item miatt nem fut) | 1480 | 13.3 | 40 |
| core | Trust_Institutions | trstprl, trstlgl, trstplc, trstplt, trstprt, trstep, trstun | 0–10 | 77, 88, 99 | mindkettő | 1149 | 4.8 | 67 |
| core | Satisfaction | stflife, stfeco, stfgov, stfdem, stfedu, stfhlth | 0–10 | 77, 88, 99 | mindkettő | 1256 | 0.8 | 44 |
| core | Policy_Attitudes | gincdif, freehms, prtyban, scnsenv | 1–5 | 7, 8, 9 | mindkettő (SL nem fut) | 1232 | 6.3 | 24 |
| core | Immigration_Policy | imsmetn, imdfetn, impcntr | 1–4 | 7, 8, 9 | mindkettő (SL nem fut) | 1378 | 40.3 | 38 |
| core | Immigration_Effects | imbgeco, imueclt, imwbcnt | 0–10 | 77, 88, 99 | mindkettő (SL nem fut) | 1261 | 16.7 | 32 |
| core | Job_Autonomy | wkdcorga, iorgact, wkdcpce | 0–10 | 66, 77, 88, 99 | mindkettő (SL nem fut) | 1219 | 39.6 | 36 |
| core | Human_Values | ipcrtiv … impfun (21 Schwartz-item) | 1–6 | 7, 8, 9 | mindkettő | 1388 | 0.2 | 129 |
| r2_health | Medicine_Approval | mdlswgt, mdhair, mdmemo, mdhappy, mdsexlf | 1–5 | 7, 8, 9 | csak Mahalanobis | 1346 | 16.0 | 27 |
| r2_health | Doctor_Attitudes | illcure, pplcure, pprlydc, psmdcpr, follwdc, dsplvpr, dckptrt, dctreql, dcdisc, ptnrlcq, dcadmms, dcdfcwr | 1–5 | 7, 8, 9 | mindkettő | 1135 | 0.0 | 44 |
| r2_econ_morality | Civic_Norms | ctzhlpo, scbevts, ctzchtx | 1–5 | 7, 8, 9 | mindkettő (SL nem fut) | 1449 | 7.5 | 45 |
| r2_econ_morality | Trust_Honest_Dealing | tstrprh, tstfnch, tstpboh | 1–5 | 7, 8, 9 | mindkettő (SL nem fut) | 1315 | 34.0 | 29 |
| r2_econ_morality | Wrongness_Judgements | pyavtxw, slcnflw, flinsrw, pbofvrw | 1–4 | 7, 8, 9 | mindkettő (SL nem fut) | 1425 | 29.0 | 50 |
| r2_econ_morality | Law_Business_Attitudes | mnyacth, olwmsop, ignrlaw, bsnprft, frmwktg, cmprcti | 1–5 | 7, 8, 9 | mindkettő | 1294 | 0.5 | 32 |
| r2_family_work | Wellbeing_Two_Weeks | gdsprt, clmrlx, actvgrs, frshrst, lfintr | 1–6 | 7, 8, 9 | csak Mahalanobis | 1486 | 10.2 | 42 |
| r2_family_work | Gender_Family_Attitudes | wmcpwrk, mnrsphm, mnrgtjb, prntghr, prrfmly | 1–5 | 7, 8, 9 | csak Mahalanobis | 1434 | 8.0 | 38 |
| r2_family_work | Housework_Feelings | tngdohm, hwkmono, chdohwk, hwkstrs | 1–5 | 6, 7, 8, 9 | mindkettő (SL nem fut) | 1296 | 4.9 | 16 |
| r2_family_work | Job_Characteristics | vrtywrk, jbrqlrn, jbscr, wgdpeft, hlpcowk, dcsfwrk, hlthrwk | 1–4 | 6, 7, 8, 9 | mindkettő | 547 | 0.2 | 21 |
| r2_family_work | Job_Demands | wrkhrd, nevdnjb, oprtad, trndnjb, wrkspv | 1–5 | 6, 7, 8, 9 | mindkettő | 556 | 1.8 | 10 |
| r2_family_work | Work_Family_Conflict | jbprtfp, pfmfdjb, dfcnswk | 1–5 | 6, 66, 77, 88, 99 | mindkettő (SL nem fut) | 462 | 24.7 | 7 |
| r2_family_work | Study_Conditions | prmpls, quclss, tchtruf, stdtruf, tchints, tchlcrt, stdask, stpvtfm, fmpvtst, stdmcdo | 1–5 | 6, 7, 8, 9 | mindkettő | 137 | 0.0 | 8 |
| r2_family_work | Job_Choice_Importance | ipjbscr, ipjbhin, ipjbprm, ipjbini, ipjbwfm | 1–5 | 6, 7, 8, 9 | csak Mahalanobis | 1276 | 22.8 | 82 |

- **Kizárási kritérium a straightlininghoz:** 5 itemes skálán az 5% feletti valós arány (Medicine_Approval, Wellbeing_Two_Weeks, Gender_Family_Attitudes, Job_Choice_Importance). Ez a felhasználó döntése.
- Az 5 itemnél rövidebb skálákon a `min_items_straightlining` miatt nem fut a straightlining. Ide tartozik a felhasználó példái közül a partnerrel való vita (365/902), a bevándorlás (210/1261) és a társadalmi bizalom (197/1480).
- **Nem skála** (a felhasználó döntése: viselkedés- vagy eseménygyakoriság, ahol a Mahalanobis valódi szélsőségeket jelöl):
  - média (tvtot…nwsppol);
  - vallásgyakorlás (rlgatnd, pray);
  - Experienced_Dishonesty (rprochg…);
  - Own_Dishonest_Behaviour (kptchng…; 70,2% straightline, kondíciószám 193);
  - Partner_Disagreement (dsgr*);
  - Medicine_Habits (hltherb, mdsdeff, prfmddc).
- Szintén nem skála a részvétel (bináris), a párt (kategoriális), az adv* (kategoriális), a darabszámok, az évszámok és a vegyes formátumú jóllétitemek (happy 0–10, sclmeet 1–7, health 1–5). Közös tartományú, többitemes core jólléti skála nincs.
- Minden skála eléri a 10 × itemszám sort (a legszorosabb a Study_Conditions: 137 ≥ 100). Szinguláris kovariancia nem fordult elő (a legnagyobb kondíciószám 33,8).

Rule-only változók:
- **`core.json`** (core, `required: true`):
  - `agea` 14–120, missing [999];
  - `yrbrn` 1880–2010, missing [7777, 8888, 9999];
  - `partner` 1–2, missing [9];
  - `icptn` 1–2, missing [9];
  - `hhmmb` 1–30, missing [77, 88, 99];
  - `gndr2` 1–2, missing [6, 7, 9];
  - `rshipa2`–`rshipa6` 1–6, missing [66, 77, 88, 99];
  - `chldhm` 1–2, missing [9].
- **`r2_family_work.json`** (rotating, `required: false`): `dsgrhwk` és `dsgrmny` 1–7, missing [66, 77, 88, 99].

### D11. Ellentmondás-szabályok (mind hangolható heurisztika)

A kódokat a value labelekből vettük. A „Találat” oszlop a valós ESS2 HU adaton mért találatszám.

| Fájl | Szabály | Indok | Találat |
| --- | --- | --- | ---: |
| core | `trstplt>8 vs trstprl<2`, `trstprt>8 vs trstplt<2`, `stfgov>8 vs stfdem<2` | a `scale_logic.json` meglévő szabályai | 1 / 1 / 0 |
| core | `partner==1 vs hhmmb==1` | a háztartási táblán partnerrel él, de egyszemélyes a háztartás | 0 |
| core | `partner==2 vs icptn==1`, `partner==1 vs icptn==2` | a háztartási tábla és a kérdezői kód ellentmond | 0 / 0 |
| core | `hhmmb==1 vs gndr2>=1` | egyszemélyes háztartásban van 2. személy | 0 |
| core | `partner==2 vs rshipaK==1` (K = 2…6) | „nem él partnerrel”, de a K. személy házastárs/partner | 0 |
| core | `chldhm==2 vs rshipaK==2` (K = 2…6) | „nem él gyerekkel”, de a K. személy gyermek | 0 |
| ess2 | `agea<=30 vs yrbrn<=1969`, `agea>=60 vs yrbrn>=1951` | 2005-ös interjúév, 5 év tűrés; körfüggő, ezért a gyökérfájlban áll | 0 / 0 |
| r2_health | `dckptrt==5 vs dcadmms==5` | „mindig eltitkolják az igazat” és „mindig beismerik a hibát” | 3 |
| r2_econ_morality | `olwmsop==1 vs ignrlaw==1`, `olwmsop==5 vs ignrlaw==5` | ellentétes jogkövetési állítások erős egyetértése / elutasítása | 14 / 3 |
| r2_family_work | `partner==2 vs dsgrhwk>=1`, `partner==2 vs dsgrmny>=1` | blokkokon átívelő: nincs partnere, mégis gyakoriságot ad a partnerrel való vitára | 3 / 3 |

- A szociodemográfiai szabályok a publikált adaton 0 találatot adnak, mert a változók részben származtatottak. Konzisztencia-őrként maradnak bent.
- **Elvetett jelöltek** (túl gyakori a valós adaton, tehát nem ellentmondás):
  - `follwdc==1 vs pprlydc==1` (141);
  - `dckptrt==1 vs dcadmms==1` (114);
  - `mnrsphm==1 vs mnrgtjb==1` (336);
  - `ctzchtx==1 vs pyavtxw==1` (40).
- A `marital==5 vs lvghw==1` szabályt is elvetettük, mert az `lvghw` csak házasoknak szól, így soha nem értékelhető.

### D12. ess_mock: a várt értékek nem változnak

A `config/scale_logic.json` nem változik, és nem állít `mahalanobis_min_scales`-t (alapérték 1), a büntetés pedig 0/1 marad. Ezért az ess_mock minden eredménye a mai:

- **Összefoglaló:** 33 / 3 gyanús (1026, 1027, 1032, mind 33.33) / 9 / 4 / 4 / 4 / 2 / 2 / 0 / átlag 87.88 / minimum 33.33.
- **Pontozott CSV:** bájtra azonos a mostanival. Nincs új oszlop, és m = 1 mellett a `detector_details` sem változik.
- **Skálatáblázat** (új riportszakasz):
  - Trust_Institutions: 5 item, `11.070498 (configured)`, 31 érvényes sor, SL 2 (1021, 1023), skálaszintű MH 3 (1005, 1026, 1033);
  - Satisfaction: 4 item, `9.487729 (configured)`, 31 érvényes sor, SL 3 (1022, 1023, 1032), skálaszintű MH 2 (1027, 1033).
- **Meglévő tesztek:** egyik sem módosul a számok miatt. Csak az AppTest-tesztek sidebar-választása változik (a „Rules source” feltöltés opciója, tasks 4.3), ha az új vezérlő ezt igényli.

### D13. Valós ESS2 adat: várható smoke-eredmény

Újraszámolva 2026-10-24-én a scratchpadből, a `.sav`-ot csak olvasva: a D10 szerinti 22 skála, alpha 0,01 és a D11 szabályai. A végleges számokat az apply rögzíti. Ellenőrzés: legalább 1 / 2 / 3 / 4 skálán 555 / 196 / 65 / 26 válaszadó jelez, ez egyezik a várt értékekkel.

A táblázat 2051, 2084 és 2307 oszlopa a három Human_Values-straightliner pontszáma.

| Logika | Gyanús (`< 50`) | Mahalanobis-jelölt | Átlag | Minimum | 2051 | 2084 | 2307 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Régi „bármelyik skála” (m = 1) | 45 (3,00%) | 555 (37,0%) | 85.31 | 0.00 | 33.33 | 66.67 | 66.67 |
| Elvetett arányos (első tervváltozat) | 0 (0,00%) | 555 (skálaarány) | 97.91 | 50.79 | 79.17 | 83.33 | 90.48 |
| m = 2 | 22 (1,47%) | 196 (13,1%) | 93.30 | 0.00 | 33.33 | 66.67 | 66.67 |
| **m = 3 (választott)** | **10 (0,67%)** | **65 (4,3%)** | **96.22** | **33.33** | **66.67** | **66.67** | **66.67** |
| m = 4 | 6 (0,40%) | 26 (1,7%) | 97.09 | 33.33 | 66.67 | 66.67 | 66.67 |

- **A három straightliner:** m = 3 mellett mindhárom 66.67 (egy detektor, a straightlining jelez), nem gyanús, de a `flag_reasons` és a skálatáblázat mutatja őket. A 2051-nek két skálán is van Mahalanobis-jelzése, ezért m ≤ 2 mellett 33.33 és gyanús.
- **A 10 gyanús összetétele m = 3 mellett:** straightlining + ellentmondás 4, straightlining + Mahalanobis 1, Mahalanobis + ellentmondás 5.
- A straightlining-jelöltek (81) és az ellentmondások (24) száma a logikától független.
- A valós adaton az értékelhető Mahalanobis-skálák száma válaszadónként legalább 4 (10. / 50. / 90. percentilis: 13 / 17 / 21; 133 válaszadónál 13-nál kevesebb). 3-nál kevesebb senkinél sincs, így m = 3 senkit nem zár ki a jelölhetőségből.
- **Miért m = 3:** a Mahalanobis-jelöltek aránya itt 4,3%, közel a spike 5%-os filozófiájához. Az m = 2 (13,1%) túl sokat, az m = 4 (1,7%) túl keveset jelöl, ezért a számok nem adtak okot az m = 3 felülvizsgálatára.

## Eldöntendő kérdések és döntések

| # | Kérdés | Lehetőségek | Döntés | Ki döntött |
| --- | --- | --- | --- | --- |
| Q1 | `mahalanobis_threshold` és `mahalanobis_alpha` együtt | (a) a threshold nyer; (b) validációs hiba | (b) hiba, és pontosan egy kötelező, ha a skálán van Mahalanobis. Indok: a fail-fast elv és a 2026-10-13-as döntés (a csendes küszöb-fallback eltávolítása) szerint egy beállítás nem maradhat csendben hatástalan. Az „egyik nyer” elfedné a konfigurációs hibát (pl. include-ban felülírt skálánál). Mahalanobis nélküli skálán bármelyik megadása is hiba. | Claude (a kérés rábízta) |
| Q2 | Részben hiányzó oszlopok `required: false` skálánál | (a) hiba; (b) a skála a meglévő oszlopokon fut; (c) a skála kimarad | (a) hiba a skála és a hiányzó oszlopok nevével. Indok: a részleges jelenlét rossz körre vagy átnevezett változóra utal. A részhalmazon futó skála csendben megváltoztatná a skála jelentését, az alpha-küszöb szabadsági fokát és a straightlining értelmét. A kihagyás pedig elrejtené a hibát. | Claude (a kérés rábízta) |
| Q3 | Contradiction-pontozás | (a) 0/1 marad; (b) arányos az értékelhető szabályok között | (a) 0/1. Indok: a szabályok kézzel írt, konzervatív, egyenként erős jelek (valós adaton 24/1498 találat). Arányosítva egy találat 1/12–1/25 súlyra hígulna. A szabályok számával az FP sem nő úgy, mint a skáláknál, mert mindegyiket közel nulla FP-re terveztük. | Claude (a kérés rábízta) |
| Q4 | A minimális sorszám alapértéke | opt-in (0) vagy alapból 10 × item | opt-in, ESS-ben 10 | Felhasználó |
| Q5 | Include a GUI-ban | beépítettkonfig-választó / csak hiba / több fájl feltöltése | beépítettkonfig-választó, feltöltött include esetén hiba | Felhasználó |
| Q6 | Khí-négyzet-kvantilis | SciPy / saját implementáció | SciPy, pinnelve | Felhasználó |
| Q7 | A „bitre azonos” spike értelmezése | a számok azonosak / a riport is bájtra azonos | az összefoglaló és a pontozott CSV bájtra azonos, a pontszámok azonosak, csak a riport kap új szakaszokat (2026-10-24-én pontosítva: a `*_penalty` oszlopok kikerültek, Q12) | Felhasználó |
| Q8 | ESS alpha | 0.05 / 0.01 / 0.001 | 0.01 | Felhasználó |
| Q9 | `flag_threshold` az arányos pontozás mellett | 60 az ESS-konfigokban / marad 50 tesztfelülírással / új fixture-sorok | **Felülírva 2026-10-24-én.** Eredetileg 60 lett volna a `scale_logic.json`-ban és az `ess2.json`-ban. Mivel az arányos pontozás kikerült (Q12), a `flag_threshold` mindenhol 50 marad, és a `config/scale_logic.json` nem változik | Felhasználó |
| Q10 | Viselkedés- és eseménygyakoriság-blokkok | nem skálák / csak Mahalanobis | nem skálák, a szabályokhoz kellő oszlopok `variables`-ként szerepelnek | Felhasználó |
| Q11 | Straightlining 5 itemes skálákon | 5 + kizárás / minimum 6 | 5, és kizárás 5% feletti valós arány esetén | Felhasználó |
| Q12 | Hogyan ne nőjön a Mahalanobis téves riasztása a skálák számával? | arányos büntetés (első tervváltozat) / 0/1 büntetés gyökérszintű `mahalanobis_min_scales` küszöbbel | 0/1: a Mahalanobis csak legalább m skálán jelezve triggerel. Az alapérték 1, az `ess2.json`-ban 3. A straightlining is 0/1, a `*_penalty` oszlopok kikerülnek. Az m = 3 Claude javaslata a D13 számai alapján (65 jelölt, 4,3%) | Felhasználó (Claude javaslata) |

## Risks / Trade-offs

- [Az m-küszöb alatt az egyes skálák Mahalanobis-jelzései nem kerülnek a pontszámba és a `flag_reasons`-ba, így egy valódi, de csak egy-két skálán kiugró válaszadó „tisztának” látszik] → Ez a szándékolt kompromisszum. A téves riasztás nem nő a skálák számával (a valós adaton 555 helyett 65 jelölt), az érzékenység pedig megmarad (50 alatt 10 gyanús). A skálaszintű jelzések a távolságoszlopokban, a `detector_details.flagged_scales`-ben és a skálatáblázatban láthatók, az m pedig hangolható.
- [Ha egy válaszadónál m-nél kevesebb skála értékelhető (pl. nem töltötte ki a szűrt rotáló blokkokat), nem kaphat Mahalanobis-jelzést] → Tudatos döntés: az m-et nem csökkentjük az értékelhető skálák számához, mert az újra a ritkán kitöltőket büntetné, vagyis ugyanaz a torzítás jönne vissza, mint az arányos büntetésnél. A valós ESS2 HU adaton ez senkit nem érint (mindenkinek legalább 4 értékelhető skálája van), és a többi detektor ilyenkor is működik. A README ezt dokumentálja.
- [A khí-négyzet-küszöb normalitást feltételez, a diszkrét ESS-itemeken a névleges arány fölött jelöl (alpha 0,01-nél skálánként 0–9%)] → Az alpha skálánként hangolható. A riport a ténylegesen használt küszöböt és forrását mutatja.
- [A `Missing_Value` számláló valós ESS-adaton nagyon magas lesz, mert a szűrt rotáló blokkok és a 6/66 („nem vonatkozik rá”) kódok hiányzónak számítanak] → A 6/66 megkülönböztetése non-goal. A README ezt dokumentálja.
- [Az SPSS-betöltő a user-missing kódokat üresnek olvassa, a missing tartományon kívüli nem tartalmi kódokat (6, 8) viszont számként] → A konfig ezeket explicit missing kódként sorolja fel (D10). CSV/XLSX-exportnál a 77/88/99 is számként jön, és ugyanúgy `Missing_Value` lesz.
- [A beemelt fájlok közös skálabeállításai ismétlődnek] → Az explicitséget vállaljuk. Egy konfig-generátor non-goal.
- [A kor–születési év sávszabályok körfüggők (2005)] → Ezért az `ess2.json` gyökérfájlban vannak, nem a `core.json`-ban.
- [A GUI csak a repó `config/` mappájának felső szintjét kínálja] → A saját moduláris konfighoz a CLI kell. A hibaüzenet ezt meg is mondja.
- [A SciPy nagy függőség egyetlen függvényért] → A felhasználó döntése; pontos és jól tesztelt.

## Migration Plan

1. Az apply elején rögzítjük az alapállapotot:
   - a spike CLI-összefoglalóját (fájlba);
   - a spike és az ess_mock teljes pontozott CSV-jének SHA-256 hash-ét;
   - a `run_spike.py` kimenetét;
   - a 91 zöld tesztet.
2. A `requirements.txt` megkapja a SciPy-t, és telepítjük.
3. Implementálás a tasks.md sorrendjében. A visszafelé kompatibilis alapértékek miatt a meglévő konfigurációk változtatás nélkül futnak, és egyik sem változik.
4. Az új riport-referenciahash-eket a `PLANNING_LOG.md`-be rögzítjük.
5. **Visszaállítás:** a change egyetlen branch-en, külön commitokban készül, így `git revert`-tel visszavonható. Adatmigráció nincs.

## Open Questions

Nincs nyitott kérdés, ami a specet, a megközelítést vagy a feladatbontást befolyásolná.
