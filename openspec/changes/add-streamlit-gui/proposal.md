## Why

A SurveyGuard jelenleg csak parancssorból (`detect_anomalies.py`) használható, ami a terminálhoz nem szokott kutatóknak és hallgatóknak belépési küszöb. Egy böngészős felülettel a fájlok feltöltése, a futtatás és az eredmények áttekintése parancsok nélkül elvégezhető. A meglévő CLI-nek közben bájtra azonos módon kell tovább működnie.

## What Changes

- Új `app.py` belépési pont a gyökérkönyvtárban: Streamlit-alkalmazás, indítása `streamlit run app.py`.
- A felület elemei:
  - fájlfeltöltő az adatfájlhoz (`.csv`, `.xlsx`, `.sav`) és a szabályfájlhoz (`.json`);
  - „Run SurveyGuard” gomb, amely csak akkor aktív, ha mindkét fájl fel van töltve;
  - Overview metrikák (`st.metric`): feldolgozott válaszadók, gyanús válaszadók, átlagos minőségi pontszám;
  - interaktív táblázatok (`st.dataframe`): detektoreredmények (darabszám és arány), illetve a detektor által jelölt válaszadók pontszámmal, gyanússági jelzővel és indokokkal;
  - letöltőgomb (`st.download_button`) a Markdown diagnosztikai jelentéshez;
  - érthető hibaüzenet (`Error: ...`) érvénytelen szabályfájl vagy adatfájl esetén, traceback nélkül.
- A GUI a meglévő csomagot hívja: `surveyguard.config.load_rules`, `surveyguard.io.load_input`, `surveyguard.scoring.score_dataframe` és a `surveyguard.reporting` modul. A detektálási vagy jelentéskészítési logika nem duplikálódik.
- A `surveyguard/reporting.py` viselkedésmegőrző refaktort kap: a Markdown-szöveg előállítása és az Overview/detektor/jelölt-válaszadó adatok kiszámítása külön, fájlírás nélküli függvényekbe kerül. A `write_report` ezeket hívja, a kimenete bájtra azonos marad.
- Új függőség: `streamlit` (Python 3.10-en `1.65.0`, 3.11-től `1.66.1`). Az `altair` a Streamlit tranzitív függősége, és grafikon nem készül, ezért külön nem rögzítjük.
- Új tesztek új fájlokban. A meglévő 46 teszt változatlanul zöld marad.
- README: új „Web interface” szakasz.

## Capabilities

### New Capabilities

- `web-interface`: a böngészős felület megfigyelhető viselkedése: feltöltés, futtatás, Overview metrikák, interaktív eredménytáblák, jelentésletöltés, hibakezelés és a CLI-vel való egyenértékűség.

### Modified Capabilities

<!-- Nincs: a `survey-quality-detection` követelményei (CLI, jelentés tartalma, detektorok) nem változnak; a reporting refaktor tisztán belső. -->

## Impact

- Új kód: `app.py`; új tesztek: `tests/test_app.py`, `tests/test_reporting_api.py`.
- Módosuló kód: `surveyguard/reporting.py` (belső szerkezet, a nyilvános `write_report` és `print_summary` viselkedése változatlan), `requirements.txt`, `README.md`.
- Változatlan: `detect_anomalies.py`, `surveyguard/cli.py`, `surveyguard/io.py`, `surveyguard/config.py`, `surveyguard/scoring.py`, `surveyguard/detectors.py`, a `prepare_data.py` / `run_spike.py` szkriptek és minden meglévő tesztfájl.
- Függőségek: a Streamlit sok tranzitív csomagot hoz (pl. `altair`, `pyarrow`, `tornado`/`starlette`), így a telepítés mérete jelentősen nő. A CLI futásához ezek nem kellenek, de a `requirements.txt` közös.
