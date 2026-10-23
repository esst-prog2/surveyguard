## 1. Függőségek

- [x] 1.1 Add hozzá a `requirements.txt`-hez: `streamlit==1.65.0; python_version < "3.11"` és `streamlit==1.66.1; python_version >= "3.11"`, egy rövid megjegyzéssel (az 1.66 Python 3.11-et követel). Ellenőrzés: `python -m pip install -r requirements.txt` hibátlan, és `python -c "import streamlit; print(streamlit.__version__)"` a várt verziót írja ki.

## 2. Reporting refaktor (viselkedésmegőrző)

- [x] 2.1 Rögzítsd az alapállapotot: futtasd a CLI-t a `--report` kapcsolóval a `tests/fixtures/survey.csv` + `tests/fixtures/rules.json` párosra, és ugyanígy a `spike_data.csv` + `config/scale_logic.json` párosra a scratchpadben. A két jelentés SHA-256 hash-ét jegyezd fel. Ellenőrzés: mindkét hash megvan a PLANNING_LOG-ban.
- [x] 2.2 A `surveyguard/reporting.py`-ban vezesd be a `ReportOverview` dataclasst, valamint a `report_overview`, `detector_results`, `flagged_respondents` és `render_report` függvényeket (lásd design 2.). A `write_report` a `render_report`-ot hívja, a `print_summary` változatlan. Ellenőrzés: `python -m pytest -q` 46 passed, és a 2.1 két jelentésének hash-e változatlan.
- [x] 2.3 Hozd létre a `tests/test_reporting_api.py` fájlt a design 9. pontjában felsorolt esetekkel: golden egyezés a `write_report` fájlja és a `render_report` között, Overview-értékek, üres keret és `N/A` átlag, detektortábla-értékek, jelölt sorrend. Ellenőrzés: `python -m pytest -q tests/test_reporting_api.py` zöld.

## 3. Streamlit-alkalmazás

- [x] 3.1 Hozd létre az `app.py`-t a `RunResult` dataclasszal és a `run_surveyguard(data_name, data_bytes, rules_bytes)` függvénnyel: ideiglenes könyvtár, rögzített fájlnevek, `load_rules` → `load_input` → `score_dataframe` → `report_overview`/`detector_results`/`flagged_respondents`/`render_report`. Ellenőrzés: `python -c "import app"` kimenet és hiba nélkül fut le.
- [x] 3.2 Írd meg a `main()`-t: két `st.file_uploader` (`type=["csv", "xlsx", "sav"]`, ill. `type=["json"]`), a hiányzó feltöltésekről tájékoztató `st.info`, és a csak két fájllal aktív „Run SurveyGuard” gomb. Futtatáskor `SurveyGuardError` → `st.error("Error: ...")`. Az eredmény a `file_id`-kulcsos `st.session_state`-be kerül. A modul alján: `if __name__ == "__main__": main()`. Ellenőrzés: `python -m streamlit run app.py` elindul, és az oldal a gombot tiltva mutatja.
- [x] 3.3 Jelenítsd meg az eredményt: három `st.metric`, a detektortábla és a jelölt válaszadók `st.dataframe`-je (`hide_index=True`, százalékformátum), üres listánál `st.info`, valamint az `st.download_button` `<stem>_diagnostics.md` névvel. Ellenőrzés: a 4.3 kézi ellenőrzése.

## 4. GUI-tesztek és ellenőrzés

- [x] 4.1 Hozd létre a `tests/test_app.py` fájlt a design 9. pontja szerint: CSV-n a CLI `--report` kimenetével bájtra egyező jelentés; azonos eredmény `.xlsx` és `.sav` bemenettel; `SurveyGuardError` érvénytelen JSON-ra és hiányzó oszlopra; nem marad ideiglenes fájl; `AppTest.from_file("app.py")` füstteszt (nincs kivétel, a gomb tiltott, a tájékoztató megjelenik), valamint teljes `AppTest` feltöltés–futtatás–letöltés–csere folyamat. Ellenőrzés: `python -m pytest -q tests/test_app.py` zöld.
- [x] 4.2 Teljes ellenőrzés:
  - `python -m pytest -q`: a 46 meglévő teszt és az új tesztek mind zöldek;
  - `git diff --stat main -- tests/test_cli.py tests/test_core.py tests/test_real_world.py tests/test_spike_scripts.py detect_anomalies.py surveyguard/cli.py surveyguard/io.py surveyguard/config.py surveyguard/scoring.py surveyguard/detectors.py` üres;
  - `python -m compileall -q surveyguard detect_anomalies.py app.py` és `git diff --check` hibátlan.

  Az eredményt rögzítsd a PLANNING_LOG-ban.
- [x] 4.3 Kézi ellenőrzés a böngészőben (`streamlit run app.py`) a `spike_data.csv` + `config/scale_logic.json` párossal, valamint ugyanennek a scratchpadben előállított `.xlsx` és `.sav` változatával:
  - a metrikák egyeznek a CLI összegzésével;
  - a letöltött jelentés hash-e egyezik a 2.1 hash-ével;
  - a letöltés után az eredmények láthatók maradnak;
  - fájlcsere után a régi eredmény eltűnik;
  - egy hibás JSON `Error:` üzenetet ad.

  Utána töröld a generált fájlokat (`git status` tiszta). Az eredményt rögzítsd a PLANNING_LOG-ban.

  *Állapot (2026-10-23):* a fenti pontokat `AppTest`-tel, valódi feltöltéssel ellenőriztük mindhárom formátumon (1000 / 2 / 96.61, a jelentés hash-e egyezik a CLI-ével, letöltés után az eredmények megmaradnak). A `python -m streamlit run app.py` szerver elindul, és HTTP 200-at ad. A valódi böngészős végigkattintást a felhasználó elvégezte, és rendben találta (2026-10-23).

## 5. Dokumentáció és validálás

- [x] 5.1 Egészítsd ki a README-t egy „Web interface” szakasszal: telepítés, `python -m streamlit run app.py`, mit mutat a felület, és hogy a CLI változatlan. Ellenőrzés: a README-ben szereplő parancs a 4.3-ban működött.
- [x] 5.2 Validáld a change-et: `openspec validate add-streamlit-gui --strict` hibamentes.
