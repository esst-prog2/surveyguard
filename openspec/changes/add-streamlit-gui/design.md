## Context

A motivációt lásd a proposal.md „Why” részében. Jelenlegi állapot:

- `surveyguard/cli.py` `main()`: `load_rules(path)` → `load_input(path, rules)` → `score_dataframe(frame, rules)` → `write_scored(...)` → `print_summary(...)` → opcionálisan `write_report(...)`. Csak a `SurveyGuardError`-t kapja el, és `Error: ...` üzenetet ír ki.
- `load_rules` és `load_input` **fájlútvonalat** vár. A `.sav` olvasása (`pd.read_spss`, mögötte `pyreadstat`) csak valódi fájlútvonallal működik, memóriapufferrel nem.
- `surveyguard/reporting.py` `write_report`: egyetlen függvényben számolja az Overview-értékeket, a detektortáblát és a jelölt válaszadók rendezett listáját, összeállítja a Markdownt, majd fájlba írja. A számoló segédfüggvények (`_detector_trigger_count`, `_data_quality_count`, `_not_scored_reason`) privátak, a GUI számára használható nyilvános API nincs.
- A felhasználói kérés a feldolgozást a „`prepare_data` és `surveyguard`” párosnak tulajdonítja. A gyökérkönyvtári `prepare_data.py` viszont a spike-adatkészlet letöltő szkriptje, nem része a feldolgozási láncnak. A feldolgozást a `surveyguard.scoring.score_dataframe` végzi, ezért a GUI ezt használja, a `prepare_data.py`-t nem.
- Az alapállapot Python 3.14.3-on 46 zöld teszt (`python -m pytest -q`).

## Goals / Non-Goals

**Goals:**
- A GUI ugyanazokat a csomagfüggvényeket hívja, mint a CLI, ezért az eredmények azonos bemenetre szükségszerűen azonosak.
- A jelentés tartalma egyetlen helyen készül: a CLI fájlba írja, a GUI letölthetővé teszi.
- A GUI üzleti logikája Streamlit-futtatókörnyezet nélkül, pytesttel tesztelhető.

**Non-Goals:**
- A pontozott CSV letöltése vagy mentése a GUI-ból. Ez később könnyen hozzáadható, de a kérésben nem szerepel.
- Grafikonok (ezért nincs közvetlen `altair`-függőség), hitelesítés, többfelhasználós telepítés, hosztolás.
- A szabályfájl szerkesztése a felületen.
- A `detect_anomalies.py`, a `surveyguard/cli.py`, az `io.py`, a `config.py`, a `scoring.py`, a `detectors.py` és bármely meglévő teszt módosítása.

## Decisions

1. **Feltöltések ideiglenes könyvtárba, a meglévő betöltők változatlanok.** Az `app.py` egy `tempfile.TemporaryDirectory()` blokkon belül rögzített nevekre írja a feltöltött bájtokat: `input<eredeti kiterjesztés kisbetűvel>` és `rules.json`. Ezután a változatlan `load_rules`/`load_input` függvényeket hívja. A blokk végén a könyvtár hiba esetén is törlődik. A feltöltött fájlnevet csak a kiterjesztés és a letöltési név képzésére használjuk, útvonalként soha, így path traversal nem lehetséges.
   *Alternatíva:* `load_input` kiegészítése fájlszerű objektumokkal. Elvetettük, mert a `.sav` olvasáshoz így is ideiglenes fájl kellene, és ezzel az `io.py` is módosulna.

2. **Viselkedésmegőrző refaktor a `reporting.py`-ban, fájlírás nélküli nyilvános függvényekkel.**
   - `report_overview(frame) -> ReportOverview` (frozen dataclass): `processed`, `suspicious`, `detector_triggered`, `missing`, `invalid`, `not_scored`, `average_score: float | None`, `minimum_score: float | None`.
   - `detector_results(frame) -> pd.DataFrame` a `Detector`, `Triggered` és `Percentage` oszlopokkal (a százalék számként, a Markdown formázza).
   - `flagged_respondents(frame, id_column) -> pd.DataFrame` a `Respondent`, `Quality score`, `Suspicious` és `Reasons` oszlopokkal, a jelentés rendezésével (pontszám szerint növekvő, stabil, NaN a végén).
   - `render_report(frame, id_column) -> str`: a fenti hármat használva állítja össze a teljes Markdownt.
   - `write_report(frame, path, id_column)`: `render_report`, majd a meglévő fájlírás és `OSError` → `DataValidationError` átalakítás.

   A meglévő privát segédfüggvények megmaradnak, a `print_summary` változatlan. Így a GUI egyetlen számítást sem ismétel meg. A bájtra azonos kimenetet a meglévő jelentéstesztek és egy új „golden” teszt védi.
   *Alternatíva:* a GUI ideiglenes fájlba írja a jelentést a `write_report`-tal, majd visszaolvassa. Elvetettük, mert az Overview metrikákat és a táblákat így a GUI-nak újra ki kellene számolnia, ami épp a tiltott kódduplikáció.

3. **Az `app.py` két rétege: tiszta futtatófüggvény és vékony Streamlit-réteg.**
   - `run_surveyguard(data_name: str, data_bytes: bytes, rules_bytes: bytes) -> RunResult`, ahol a `RunResult` (frozen dataclass) mezői `overview`, `detectors`, `flagged`, `report_markdown`, `report_file_name`, valamint a `report_bytes` tulajdonság. Streamlit-hívást nem tartalmaz, ezért közvetlenül tesztelhető. A `SurveyGuardError`-t továbbengedi.
   - `main()`: a Streamlit-elemek. A modul alján `if __name__ == "__main__": main()` áll. A `streamlit run` a szkriptet `__main__` néven futtatja, a teszt importja viszont nem indít UI-t.

   A nem támogatott kiterjesztést a feltöltő `type=` szűrője és a `load_input` meglévő ellenőrzése is kiszűri.

4. **Session state a letöltés utáni újrafuttatás miatt.** A Streamlit minden interakcióra (a letöltőgomb kattintására is) újrafuttatja a szkriptet. A `RunResult` ezért az `st.session_state`-be kerül, a két feltöltés `file_id`-jéből képzett kulccsal. Ha bármelyik feltöltés megváltozik vagy eltűnik, a kulcs nem egyezik, és a régi eredmény nem jelenik meg. Hiba esetén a tárolt eredmény törlődik.
   *Alternatíva:* `st.cache_data` a futtatásra. Elvetettük, mert az eredmény a gombnyomáshoz kötött, nem a bemenethez, és a cache a feltöltött adatot a session után is megtartaná.

5. **Hibakezelés a CLI mintájára.** A `main()` csak a `SurveyGuardError`-t kapja el, és `st.error(f"Error: {exc}")` üzenetet mutat. Minden más kivétel propagál (a Streamlit fejlesztői tracebacket mutat), `except Exception` nincs. Ez a projekt korábbi döntésével (2026-10-13, 2026-10-20) egyezik.

6. **Megjelenítés.**
   - Három `st.metric` egy sorban (`st.columns(3)`): „Processed respondents”, „Suspicious respondents”, „Average quality score” (két tizedes vagy `N/A`; a formázás a `reporting` meglévő `_format_metric` logikáját követi).
   - Detektortábla: `st.dataframe(..., hide_index=True)`, a `Percentage` oszlop `st.column_config.NumberColumn(format="%.2f%%")` formátumú.
   - Jelölt válaszadók táblája: `st.dataframe(..., hide_index=True)`; ha üres, `st.info("No respondents were flagged.")`.
   - Az UI-szövegek angolok, a CLI-hez és a jelentéshez igazodva.

7. **Letöltés.** `st.download_button("Download diagnostic report", data=result.report_bytes, file_name=f"{Path(data_name).stem}_diagnostics.md", mime="text/markdown")`. A `report_bytes` a `report_markdown` `
` sorvégeit `os.linesep`-re cseréli, majd UTF-8-ként kódolja. *Megvalósítás közben derült ki:* a CLI `write_text`-je a platform sorvégét írja (Windowson CRLF). Ezért a sima `.encode("utf-8")` Windowson nem adna bájtra azonos fájlt, a spec viszont ezt követeli meg. A CLI nem változhat, így a GUI igazodik hozzá.

8. **Függőségrögzítés a meglévő mintát követve.** `streamlit==1.65.0; python_version < "3.11"` és `streamlit==1.66.1; python_version >= "3.11"`. Az 1.66.x már Python ≥ 3.11-et követel, a repo viszont a 3.10-et is támogatja. Egy dry-run feloldás szerint az 1.66.1 a meglévő pinekkel (pandas 3.0.2, numpy 2.4.4) ütközés nélkül telepíthető. Az `altair` tranzitív függőség, és nem rajzolunk vele, ezért nem pineljük.

9. **Tesztelés, csak új fájlokban.**
   - `tests/test_reporting_api.py`:
     - a `render_report` kimenete bájtra egyezik a `write_report` fájljával;
     - a `report_overview`, `detector_results` és `flagged_respondents` értékei egy ismert fixture-ön, beleértve az üres keretet és az `N/A` átlagot;
     - a jelölt válaszadók sorrendje egyezik a jelentésével.
   - `tests/test_app.py`:
     - `run_surveyguard` a `tests/fixtures/survey.csv` és `rules.json` fájlokkal: a jelentés bájtra egyezik a CLI `--report` kimenetével;
     - `.xlsx` és `.sav` bemenet (a teszt `tmp_path`-ban állítja elő) ugyanazt az eredményt adja;
     - érvénytelen JSON és hiányzó oszlop esetén `SurveyGuardError` keletkezik;
     - futás után nem marad ideiglenes fájl (a `tempfile.tempdir` `tmp_path`-ra van monkeypatch-elve);
     - a `streamlit.testing.v1.AppTest` füstteszt: az `app.py` kivétel nélkül renderel, a futtatógomb tiltott, és megjelenik a hiányzó feltöltésekről szóló tájékoztatás;
     - teljes `AppTest` folyamat: feltöltés, futtatás, a metrikák és táblák ellenőrzése, letöltés után a megmaradó eredmény, majd fájlcsere és hibás JSON esetén az eredmény eltűnése és az `Error:` üzenet.

   *Megvalósítás közben derült ki:* az `AppTest` a rögzített 1.65.0 és 1.66.1 verzióban is támogatja a fájlfeltöltést (`file_uploader[i].upload(...)`) és a letöltőgomb kattintását. Így a feltöltés utáni UI-ágat is automatikus teszt fedi. A tervezéskor ezt még nem tudtuk.

## Risks / Trade-offs

- [A `reporting.py` refaktor véletlenül megváltoztathatja a jelentés bájtjait.] → A meglévő jelentéstesztek változatlanul futnak, és egy új golden teszt a CLI által írt fájlt hasonlítja a `render_report` kimenetéhez.
- [Az `AppTest` nem valódi böngésző, így a tényleges letöltött fájlt és a böngészős megjelenést nem ellenőrzi.] → A letöltött bájtokat a `run_surveyguard` tesztje veti össze a CLI fájljával; a böngészős végigkattintás kézi ellenőrzés marad (tasks 4.3).
- [A Streamlit nagy függőségfát hoz, és a CLI-felhasználók is telepítik.] → Elfogadható egy egyetlen `requirements.txt`-t használó kurzusprojektben. Ha zavaró lesz, később szétválasztható (pl. `requirements-gui.txt`).
- [Nagy feltöltések memóriában.] → A Streamlit alapértelmezett 200 MB-os korlátja marad. A CLI ugyanezt a pandas-betöltést használja, így új korlátot nem vezetünk be.
- [Valódi, személyes adatot tartalmazó felmérés feltöltése.] → Az adat csak a futás idejére, ideiglenes könyvtárban kerül lemezre, és a session state-ben csak az aggregált eredmény meg a jelentés marad. A repóba nem kerül adat (lásd „Protect repository data privacy”).

## Migration Plan

Nincs migráció: a CLI változatlan. Telepítés: `python -m pip install -r requirements.txt`, majd `python -m streamlit run app.py`. (A pip a `streamlit.exe`-t nem feltétlenül teszi a PATH-ra.) Visszaállítás: az `app.py`, a két új tesztfájl és a Streamlit-sorok eltávolítása. A `reporting.py` refaktor visszaállítás nélkül is kompatibilis marad.
