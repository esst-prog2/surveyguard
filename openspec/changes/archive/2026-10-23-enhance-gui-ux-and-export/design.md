## Context

A motivációt lásd a proposal.md „Why” részében. Jelenlegi állapot (az `add-streamlit-gui` alkalmazása után, commit nélkül):

- `app.py`:
  - `run_surveyguard(data_name, data_bytes, rules_bytes) -> RunResult` Streamlit-hívás nélkül fut;
  - a `show_result(result)` jeleníti meg a metrikákat, a két táblát és a jelentésletöltést;
  - a `main()` egyetlen oszlopba rakja a feltöltőket, a tájékoztatót, a gombot és az eredményt;
  - az eredmény a `st.session_state["surveyguard_run"]`-ban van, a két feltöltés `file_id`-jével kulcsolva, így minden widget-interakció utáni újrafuttatást túlél.
- A `run_surveyguard` a betöltött bemeneti keretet (`frame`) és a pontozott keretet (`scored`) is ismeri. A `score_dataframe` a `frame` sorrendjét megtartja, az indexet `reset_index(drop=True)`-val állítja vissza. A `scored["suspicious"]` `boolean` típusú, a pontozatlan sorokban `<NA>` (lásd `surveyguard/scoring.py`). A `suspicious` jelző jelentése `quality_score < flag_threshold` (alapértelmezés: 50).
- A `tests/test_app.py` AppTest-tesztjei az `app.button[0]`, `app.file_uploader[i]` és `app.info[0]` elemekre hivatkoznak. Az oldalsávba költöztetés után az `info[0]` már a főoldali útmutatóra mutatna, ezért ezek a tesztek frissítendők.
- Mindkét rögzített Streamlit-verzió (1.65.0 és 1.66.1) `st.bar_chart`-ja támogatja az `x`, `y`, `x_label`, `y_label` és `sort` paramétert. Az AppTest mindkettőben kezeli az oldalsávot (`app.sidebar`) és a toggle-t.
- Jóváhagyott döntések (2026-10-23): a felület végig angol; a tisztított fájl mindig CSV, az eredeti oszlopokkal.

## Goals / Non-Goals

**Goals:**
- Minden új funkció az `app.py`-ban valósul meg. A `surveyguard` csomag és a CLI bájtra változatlan.
- A tisztított CSV a pontozó által már kiszámolt `suspicious` jelzőből készül, nem számolunk újra küszöböt.
- Az új UI-viselkedést az AppTest automatikusan teszteli.

**Non-Goals:**
- XLSX vagy SAV formátumú tisztított export, vagy pontszám-oszlopok a tisztított fájlban (jóváhagyott döntés).
- Az eltávolítási küszöb állítása a felületen. A szabályfájl `flag_threshold` értéke dönt.
- További grafikonok, egyedi színpaletta, közvetlen `altair`-használat.
- A korábbi kérésből maradt 4.3-as kézi böngészős ellenőrzés kiváltása. Az az `add-streamlit-gui` része marad.

## Decisions

1. **Elrendezés: `with st.sidebar:` blokk a vezérlőknek, a főoldalon az útmutató és az eredmények.**
   - Az oldalsávba kerül: `st.header("Inputs")`, a két `st.file_uploader`, a hiányzó feltöltésekről szóló `st.info` és a „Run SurveyGuard” gomb.
   - A főoldalon marad: `st.title`, `st.caption`, és ha nincs megjeleníthető eredmény, `st.info("Upload the response data and rules files in the sidebar, then click Run SurveyGuard.")`. Ide kerül a spinner, a siker- vagy hibaüzenet és az eredmény is.

   *Alternatíva:* `st.sidebar.file_uploader(...)` hívások egyenként. Ugyanazt adja, de a `with` blokk egy helyen tartja a vezérlőket.

2. **Spinner és sikerüzenet a főoldalon, csak a futtató újrafuttatásban.**
   - A gombnyomás ága: `with st.spinner("Processing data..."): result = run_surveyguard(...)`, siker esetén `st.success("Analysis complete!")`. A `with` blokk az oldalsávon kívül van, így a spinner és az üzenet a főoldalon jelenik meg.
   - A sikerüzenet nem kerül a session state-be: a következő interakció (toggle, letöltés) után eltűnik, az eredmény viszont megmarad.
   - Hiba esetén nincs sikerüzenet, csak `st.error`.

   *Alternatíva:* tartós sikerüzenet minden olyan újrafuttatásban, ahol eredmény látszik. Elvetettük, mert az „Analysis complete!” toggle-váltás után már nem friss esemény, csak zaj.

3. **Szűrő-kapcsoló: `st.toggle("Show suspicious respondents only", key="suspicious_only")` közvetlenül a jelölt-táblázat fölött.**
   - Csak akkor jelenik meg, ha a jelölt-tábla nem üres.
   - Bekapcsolva a megjelenített tábla `result.flagged[result.flagged["Suspicious"]]`. A rendezés így megmarad, mert a `flagged` már a jelentés sorrendjében van.
   - Ha a szűrt tábla üres: `st.info("No respondents are suspicious.")`.
   - A szűrés csak a megjelenítést érinti; a `RunResult` és a letöltések nem változnak. A kapcsoló újrafuttatást vált ki, de a session state-ben tárolt eredmény miatt nem fut új elemzés.

4. **Grafikon: `st.bar_chart` közvetlen `altair` nélkül.**
   - Hívás: `st.bar_chart(result.detectors, x="Detector", y="Percentage", x_label="Detector", y_label="Respondents triggered (%)", sort=False)`.
   - A `sort=False` a tábla sorrendjét tartja (Straightlining, Contradiction, Mahalanobis), nem ábécérendet.
   - A detektortábla és a grafikon egymás mellett, `st.columns(2)`-ben van; keskeny képernyőn a Streamlit egymás alá rendezi őket.
   - Az implementáció előtt a `dataviz` skillt be kell tölteni, és a grafikont az ott leírtak szerint kell ellenőrizni.

   *Alternatíva:* közvetlen `altair`-diagram fix 0–100%-os tengellyel és címkékkel a hasábokon. Elvetettük, mert közvetlen importhoz az `altair`-t pinelni kellene (a 2026-10-23-i döntés szerint tranzitív és pineletlen), és a feladat egy „letisztult” diagram.

5. **Tisztított CSV a `run_surveyguard`-ban, a csomagon kívül.**
   - A `RunResult` új mezői: `cleaned_csv: bytes`, `cleaned_file_name: str` (`f"{Path(data_name).stem}_cleaned.csv"`), `removed_count: int` és `kept_count: int`.
   - Számítás: `keep = ~scored["suspicious"].fillna(False).to_numpy(dtype=bool)`, majd `frame.iloc[keep].to_csv(index=False).encode("utf-8")`. A `frame` a `load_input` által betöltött keret, normalizálás nélkül. Így az eredeti oszlopok, sorrend és értékek maradnak (SPSS-nél raw kódok), pontozó oszlop nélkül. A pontozatlan (`<NA>`) sorok megmaradnak.
   - A pandas alapértelmezett sorvégét (`os.linesep`) használjuk, ugyanúgy, mint a CLI `write_scored`-ja.
   - Lemezre semmi nem íródik.

   *Alternatíva:* `filter_suspicious()` a `surveyguard` csomagban. Elvetettük, mert a kérés a maglogika érintetlenségét követeli, és egy maszkolás nem üzleti logika.
   *Alternatíva:* szűrés `quality_score < 50` alapján. Elvetettük, mert a `flag_threshold` konfigurálható, és a `suspicious` oszlop már ezt tükrözi.

6. **Két letöltőgomb egymás mellett.** `st.columns(2)`: balra a „Download diagnostic report”, jobbra a „Download cleaned data (CSV)” (`mime="text/csv"`). Alattuk `st.caption(f"Cleaned data: removed {removed_count} suspicious respondents, kept {kept_count}.")`.

7. **Tesztek.**
   - A `tests/test_app.py` meglévő AppTest-tesztjei explicit oldalsáv-hivatkozást kapnak (`app.sidebar.file_uploader[i]`, `app.sidebar.button[0]`, `app.sidebar.info[0]`), és ellenőrzik, hogy a főoldalon nincs feltöltő. Ez szándékos, a felhasználó által engedélyezett módosítás. A többi tesztfájl változatlan.
   - A folyamattesztben ellenőrizzük, hogy futás után megjelenik az `app.success[0].value == "Analysis complete!"`, hibás JSON-nál pedig nincs `success`.
   - Új `run_surveyguard`-tesztek egy kibővített adathalmazon: a fixture CSV-t a teszt kiegészíti két garantáltan gyanús sorral (`5,5,5,5` és `1,1,1,1`: straightlining és ellentmondás egyszerre). Ellenőrizzük:
     - a pontos eltávolított azonosítókat, a `removed_count`/`kept_count` értéket és a megmaradt sorrendet;
     - hogy az oszlopok egyeznek a bemenetéivel;
     - a gyanús sor nélküli esetet (0 eltávolítva, minden sor megvan);
     - hogy az `.xlsx`/`.sav` bemenet ugyanazt adja, mint a `.csv`, `pd.read_csv` után dtype-ellenőrzés nélkül összevetve (a SAV raw kódjai floatként, pl. `3.0` formában jönnek);
     - hogy a fájlnév `<stem>_cleaned.csv`.

     A pontos gyanús azonosítókat az implementáció kézzel ellenőrzi a pontszámokból.
   - Új AppTest-tesztek:
     - a toggle alapból ki van kapcsolva; bekapcsolva csak a gyanús sorok maradnak, kikapcsolva visszajön a teljes lista;
     - gyanús sor nélküli adaton bekapcsolva a „No respondents are suspicious.” üzenet jelenik meg;
     - pontosan egy Vega-Lite grafikon van, és a specifikációja a `Detector`/`Percentage` mezőkre hivatkozik;
     - két letöltőgomb van, és megjelenik a felirat a darabszámokkal.

   A spinner átmeneti elem, az AppTest nem rögzíti. Ezt kódellenőrzés és a kézi böngészős próba fedi.

## Risks / Trade-offs

- [Az `st.bar_chart` tengelye automatikusan skálázódik, így kis százalékok (pl. 2%) is magas hasábnak látszhatnak.] → Az y-tengely címkéje jelzi a százalékot, és mellette ott a pontos tábla. Ha zavaró, egy későbbi change áttérhet pinelt `altair`-re.
- [A tisztított CSV pandas-újraírás, nem a feltöltött fájl bájtjainak másolata: egész szám és hiányzó érték keveredésénél float lehet, idézőjelezés és dátumformátum változhat.] → A cél a további elemzés, nem a bájthűség. Dokumentáljuk a README-ben. A sorok és oszlopok azonosak.
- [A gyanús kitöltők eltávolítása után a megmaradt adat Mahalanobis-statisztikája megváltozna, ha újra futtatnák.] → Ez szándékos, és nem a GUI felelőssége; a README megemlíti.
- [Az AppTest nem látja a spinnert.] → Kódellenőrzés és kézi próba.

## Migration Plan

1. **Előfeltétel:** az `add-streamlit-gui` change-et előbb le kell zárni (4.3 kézi ellenőrzés), commitolni és archiválni kell. Csak így jön létre az `openspec/specs/web-interface/spec.md`, amelyre ennek a change-nek a `MODIFIED` deltái hivatkoznak. Az `openspec validate --strict` most is hibátlan, de jelzi, hogy az archiválás addig elutasítaná a deltát.
2. Az implementáció a jelenlegi `app.py`-ra épül. Futásidejű migráció nincs, a CLI és a csomag változatlan.
3. Visszaállítás: az `app.py` és a `tests/test_app.py` előző változatára való visszatérés.
