## Why

Az első Streamlit-felület (`add-streamlit-gui`) működik, de a vezérlők és az eredmények egyetlen oszlopban keverednek, és a futtatás alatt nincs visszajelzés. A jelölt kitöltők listájából nem lehet csak a gyanúsakat kiszűrni, a detektorarányokat pedig csak táblázatból lehet leolvasni. A legfontosabb hiány, hogy az elemzés után a felhasználónak magának kell kiszűrnie a gyanús kitöltőket az adatfájlból a további elemzéshez.

## What Changes

- **Oldalsáv:** a két fájlfeltöltő, a hiányzó feltöltésekről szóló tájékoztatás és a „Run SurveyGuard” gomb az `st.sidebar`-ba kerül. A főoldalon csak a cím, az útmutató, a visszajelzések és az eredmények maradnak.
- **Visszajelzés:** a futtatás egy `st.spinner("Processing data...")` blokkban zajlik, siker után `st.success("Analysis complete!")` jelenik meg. A felület végig angol, a jóváhagyott döntés szerint.
- **Szűrés:** a jelölt kitöltők táblázata fölé `st.toggle("Show suspicious respondents only")` kerül. Bekapcsolva csak azok a sorok látszanak, ahol a `Suspicious` értéke igaz.
- **Vizualizáció:** a detektortábla mellé `st.bar_chart` kerül, amely detektoronként a `Percentage` oszlopot mutatja, a táblázat sorrendjében.
- **Tisztított adat exportja:** a jelentés letöltőgombja mellé egy második `st.download_button` kerül, amely a `<feltöltött fájl neve>_cleaned.csv` fájlt adja. Ebből minden gyanús kitöltő (`quality_score < 50`) ki van szűrve. A fájl a feltöltött adat eredeti oszlopait és értékeit tartalmazza, mindig CSV-ként, a bemeneti formátumtól függetlenül.
- A `tests/test_app.py` meglévő AppTest-tesztjei az oldalsávra kerülő elemek pontos helyét is ellenőrzik. Új tesztek fedik a szűrést, a grafikont, a visszajelzéseket és a tisztított exportot.

## Capabilities

### New Capabilities

<!-- Nincs. -->

### Modified Capabilities

- `web-interface`: a vezérlők az oldalsávba kerülnek, a jelölt-táblázat szűrhető lesz, és új követelmény lesz a futtatási visszajelzés, a detektorarány-grafikon és a tisztított adat letöltése. Ez a képesség az `add-streamlit-gui` change-ből származik, amely még nincs archiválva (lásd design.md, „Migration Plan”).

## Impact

- Módosuló kód: `app.py` (elrendezés, új UI-elemek, a `RunResult` bővítése a tisztított CSV-vel), `tests/test_app.py`, `README.md`.
- Változatlan: `detect_anomalies.py` és a teljes `surveyguard` csomag (a `reporting.py` is), a többi tesztfájl és a `requirements.txt`. Az `st.bar_chart` a már telepített, tranzitív `altair`-t használja, közvetlen import nélkül.
- Nincs új fájl a lemezen: a tisztított CSV is csak memóriában készül, és letöltéssel jut a felhasználóhoz.
