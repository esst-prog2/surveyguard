## Why

A Streamlit felület ma csak táblázatokat és egyetlen detektor-oszlopdiagramot mutat. A kutató nem látja egyben a minőségi pontszámok eloszlását, nem látja, hol helyezkednek el a Mahalanobis-kiugrók a többi válaszadóhoz képest, és egy megjelölt kitöltő okát (egyenesvonalú kitöltés, logikai ellentmondás) csak az okszövegből tudja kikövetkeztetni. Egy vizuális analitikai réteg ezeket a döntéseket gyorsítja. A pontozást és a parancssoros eszközt közben nem szabad lassítani vagy megváltoztatni.

## What Changes

- **Új modul: `surveyguard/visualization.py`.** Tiszta függvényekből áll, amelyek a futás eredményéből (pontozott tábla, feloldott szabályok) Plotly-ábrákat és táblákat készítenek. Az `app.py` csak meghívja és megjeleníti őket. A pontozó modulok (`scoring.py`, `detectors.py`, `reporting.py`, `io.py`, `config.py`) és a CLI nem változnak, és nem importálják az új modult.
- **Új függőség a `requirements.txt`-ben:** `plotly` (ábrák), pontos verzióval, a meglévő stílusban (3.10 támogatás megmarad). A PCA a már pinelt `numpy` SVD-jével készül, új könyvtár nélkül.
- **Minőségi pontszám-eloszlás:** hisztogram a pontozott válaszadók `quality_score` értékeiről, piros szaggatott függőleges vonallal a konfigurált `flag_threshold` értékénél (alapból 50).
- **Mahalanobis PCA-térkép:** választható Mahalanobis-skálánként 2D-s pontfelhő az első két főkomponensen, pontosan azokon a sorokon, amelyekre a detektor távolságot számolt. A szín a látott skáláról szól: piros, aki ezen a skálán kiugró (a távolsága nagyobb a skála küszöbénél), a többi szürke. A válaszadó szintű Mahalanobis-jelzést (legalább m skálán kiugró) külön jelölőforma és körvonal mutatja, a jelmagyarázat mindkettőt megnevezi. A tooltip az azonosítót (`id_column`, ennek hiányában a sorszámot), a skála távolságát és küszöbét, valamint a két jelzést mutatja; az ábra alatti felirat elmagyarázza, miért lehet egy skálán kiugró pont a térkép közepén. A vetület csak a kiválasztott skálára, igény szerint számolódik és futásonként gyorsítótárazódik.
- **Straightlining-hőtérkép:** ha a megjelölt válaszadók táblájában a felhasználó kiválaszt egy straightlining miatt megjelölt sort, megjelenik egy hőtérkép a válaszadó megjelölt skáláinak itemértékeivel. Az azonos értékek azonos színt kapnak, és a cellák az értéket is kiírják.
- **Válaszadói drill-down:** legördülő lista a megjelölt válaszadók táblájának soraiból, ugyanabban a sorrendben, a meglévő „Show suspicious respondents only” szűrőt követve (kikapcsolva minden jelölt, bekapcsolva csak a gyanúsak); a gyanúsak címkéje `suspicious` jelölést kap. A kiválasztott válaszadónál megjelenik a pontszám, az okok detektoronként, és a logikai ellentmondások táblája szabályonként: oszlop, a válaszadó értéke, a feltétel, kiemelve.
- **OpenSpec:** a `web-interface` specifikáció új követelményeket kap a fenti négy vizuális elemhez, és egy követelményt arról, hogy a vizuális réteg nem befolyásolja a pontozást és a CLI-t.
- **Tesztek:** új `tests/test_visualization.py` (ábragenerálás, sorhalmazok, színek, küszöbvonal, drill-down tábla, a CLI importizolációja) és AppTest-esetek. A meglévő tesztek (jelenleg 358, köztük a `test_fast_scoring.py`) változtatás nélkül zöldek maradnak.

## Capabilities

### New Capabilities

Nincs.

### Modified Capabilities

- `web-interface`: új követelmények a pontszám-eloszlás hisztogramjára, a Mahalanobis PCA-térképre, a straightlining-hőtérképre, a válaszadói drill-down-ra, valamint arra, hogy a vizuális elemek nem változtatják a pontozást, a riportot és a parancssoros működést.

## Impact

- **Kód:** új `surveyguard/visualization.py`; az `app.py` `RunResult`-ja kiegészül a vizualizációhoz szükséges adatokkal (pontozott tábla, feloldott szabályok, küszöb), és új szekciókat jelenít meg. A pontozó, riportoló és CLI-modulok nem változnak.
- **Függőségek:** `plotly` (csak a webes felület használja; a CLI importja nem tölti be). A PCA-hoz nincs új függőség.
- **Tesztek:** új `tests/test_visualization.py`, új AppTest-esetek; a meglévő tesztfájlok nem módosulnak.
- **Dokumentáció:** README webes felület szakasza; `PLANNING_LOG.md`.
- **Teljesítmény:** a pontozás ideje nem változik; a vizuális számítások lustán, csak a megjelenített elemekhez futnak.
