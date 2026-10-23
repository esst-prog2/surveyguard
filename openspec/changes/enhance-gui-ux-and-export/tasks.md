## 1. Előfeltétel

- [ ] 1.1 Zárd le az `add-streamlit-gui` change-et: a felhasználó elvégzi a 4.3 kézi böngészős ellenőrzést, a változások egy új ágon (pl. `feat-streamlit-gui`) commitba kerülnek, majd a change archiválódik. Ellenőrzés: létezik az `openspec/specs/web-interface/spec.md`, és az `openspec validate enhance-gui-ux-and-export --strict` már nem ad „target spec does not exist” jelzést.
- [ ] 1.2 Rögzítsd az alapállapotot: `python -m pytest -q` → 59 passed, és a CLI-jelentés hash-ei egyeznek a PLANNING_LOG-ban rögzítettekkel (`eac61674…`, `eacf48fc…`). Ellenőrzés: az eredmény bekerül a PLANNING_LOG-ba.

## 2. Tisztított adat (`run_surveyguard`)

- [ ] 2.1 Bővítsd a `RunResult`-ot a `cleaned_csv`, `cleaned_file_name`, `removed_count` és `kept_count` mezőkkel, és számold ki őket a `run_surveyguard`-ban a design 5. pontja szerint (`frame.iloc[keep]`, a `suspicious` `<NA>` → megtartva). Ellenőrzés: `git diff --stat -- surveyguard detect_anomalies.py` üres.
- [ ] 2.2 A `tests/test_app.py`-ban add hozzá a tisztított adat tesztjeit a design 7. pontja szerint: két gyanús sorral kibővített adathalmaz; pontos eltávolított azonosítók, darabszámok és sorrend; oszlopegyezés; 0 gyanús eset; `.xlsx`/`.sav` = `.csv`; `<stem>_cleaned.csv` név; nem marad fájl az ideiglenes könyvtárban. Ellenőrzés: `python -m pytest -q tests/test_app.py` zöld.

## 3. Felület

- [ ] 3.1 Helyezd át a feltöltőket, a hiányzó feltöltésekről szóló tájékoztatót és a „Run SurveyGuard” gombot egy `with st.sidebar:` blokkba (`st.header("Inputs")`). Eredmény nélkül a főoldalon az útmutató `st.info` jelenjen meg. Frissítsd a meglévő AppTest-teszteket explicit `app.sidebar.*` hivatkozásokra, és ellenőrizd, hogy a főoldalon nincs feltöltő. Ellenőrzés: `python -m pytest -q tests/test_app.py` zöld.
- [ ] 3.2 Tedd a `run_surveyguard` hívást egy `with st.spinner("Processing data..."):` blokkba a főoldalon, siker után `st.success("Analysis complete!")` jelenjen meg, hiba esetén ne. Ellenőrzés: a folyamatteszt ellenőrzi a `success` jelenlétét sikeres futás után és a hiányát hibás JSON-nál.
- [ ] 3.3 Töltsd be a `dataviz` skillt, majd tedd a detektortábla mellé (`st.columns(2)`) az `st.bar_chart(..., x="Detector", y="Percentage", x_label="Detector", y_label="Respondents triggered (%)", sort=False)` grafikont. Ellenőrzés: egy AppTest-teszt pontosan egy Vega-Lite grafikont talál, amelynek specifikációja a `Detector` és `Percentage` mezőkre hivatkozik.
- [ ] 3.4 Tedd a jelölt-tábla fölé az `st.toggle("Show suspicious respondents only", key="suspicious_only")` kapcsolót (csak nem üres táblánál). Bekapcsolva csak a `Suspicious == True` sorok látsszanak, üres szűrt táblánál `st.info("No respondents are suspicious.")` jelenjen meg. Ellenőrzés: AppTest-tesztek a ki-be kapcsolásra, a sorrendre és az üres esetre.
- [ ] 3.5 Tedd a két letöltőgombot `st.columns(2)`-be: „Download diagnostic report” és „Download cleaned data (CSV)” (`mime="text/csv"`), alattuk a darabszámos `st.caption`-nel. Ellenőrzés: egy AppTest-teszt két letöltőgombot és a helyes feliratot találja, és mindkét gomb kattintása után megmaradnak az eredmények.

## 4. Ellenőrzés és dokumentáció

- [ ] 4.1 Teljes ellenőrzés:
  - `python -m pytest -q`: az 59 korábbi teszt (a `test_app.py` oldalsáv-frissítésével) és az új tesztek mind zöldek;
  - `git diff --stat main -- surveyguard detect_anomalies.py requirements.txt tests/test_cli.py tests/test_core.py tests/test_real_world.py tests/test_spike_scripts.py tests/test_reporting_api.py` üres;
  - `python -m compileall -q surveyguard detect_anomalies.py app.py` és `git diff --check` hibátlan;
  - a CLI-jelentés hash-ei változatlanok.

  Az eredményt rögzítsd a PLANNING_LOG-ban.
- [ ] 4.2 Ellenőrizd a spike-adattal (CSV, valamint a scratchpadben előállított XLSX és SAV) AppTest-tel:
  - a tisztított CSV pontosan a `processed − suspicious` sort tartalmazza;
  - XLSX és SAV esetén ugyanazokat a sorokat adja, mint CSV esetén;
  - a grafikon három hasábja a detektortábla százalékait mutatja.

  Utána töröld a generált fájlokat, és rögzítsd az eredményt a PLANNING_LOG-ban.
- [ ] 4.3 Kézi böngészős ellenőrzés (`python -m streamlit run app.py`): oldalsáv-elrendezés, spinner, sikerüzenet, toggle, grafikon, mindkét letöltés, és telefonszélességen (kb. 390 px) a két oszlop egymás alá rendeződése. Ellenőrzés: az eredmény bekerül a PLANNING_LOG-ba.
- [ ] 4.4 Frissítsd a README „Web interface” szakaszát: oldalsáv, szűrő, grafikon és tisztított CSV (mit tartalmaz, mi kerül ki, a pandas-újraírás korlátai). Ellenőrzés: a leírt lépések egyeznek a 4.3-ban látottakkal.
- [ ] 4.5 Validáld a change-et: `openspec validate enhance-gui-ux-and-export --strict` hibamentes.
