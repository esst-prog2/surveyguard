## 1. Előkészítés és függőségek

- [x] 1.1 Új ág `feat-visual-analytics` a `main`-ből; ellenőrzés: `git branch --show-current` kimenete `feat-visual-analytics`
- [x] 1.2 Kiinduló állapot a PLANNING_LOG-ba: `pytest -q` eredménye és ideje (várhatóan 358 teszt), a `tests/fixtures/ess_mock.csv` + `config/scale_logic.json` CLI-futás pontozott CSV-jének és riportjának SHA-256 hash-e; ellenőrzés: a sor a logban
- [x] 1.3 `requirements.txt`: `plotly` pontos verzióval (D1), szükség esetén Python-jelölővel, rövid megjegyzéssel; `scikit-learn` nem kerül be; ellenőrzés: `pip install -r requirements.txt` sikeres Python 3.14-en, a `python -c "import plotly, streamlit"` hibátlan, a választott verzió a PLANNING_LOG-ban

## 2. `surveyguard/visualization.py` – adat-előkészítés

- [x] 2.1 `flagged_positions(scored)` a `flagged_respondents` rendezésével (D6); ellenőrzés: teszt, hogy a pozíciókból képzett azonosítók sorrendje megegyezik a `flagged_respondents(...)["Respondent"]`-tel a fixture-ön, `id_column`-nal és nélküle
- [x] 2.2 `analysis_frame(frame, rules)` a `resolve_rules` és a `_normalise_questions` hívásával (D3); ellenőrzés: teszt, hogy a hiánykód és a tartományon kívüli érték NaN, a többi érték változatlan

## 3. Ábrák és táblák

- [x] 3.1 `score_histogram(scored, flag_threshold)` (D4); ellenőrzés: tesztek a bin-beállításra (0–100, 5), az összdarabszámra = pontozott sorok, a piros szaggatott vonalra 50-nél és 60-nál, a kihagyott sorok számára és a nincs-pontszám esetre
- [x] 3.2 `pca_projection(values)` numpy SVD-vel a D5 előjelszabályával és `pca_map(analysis, scored, scale_config, min_scales, id_column)` (D5) `Scattergl`-lel: szín = skálaszintű kiugró (távolság > küszöb), rombusz + fekete körvonal = `mahalanobis_outlier_triggered`, csak jelmagyarázatbeli nyomvonal a jelölőhöz, hover és felirat; ellenőrzés: tesztek a fixture-ön, hogy a pontok sorai = a nem-NaN `mahalanobis_distance_<skála>` sorai, a piros pontok száma = a skálatábla „Mahalanobis flags (scale-level)” értéke, a kiemelt jelölők = `mahalanobis_outlier_triggered`, a jelmagyarázat neve „Outlier on this scale” és „Mahalanobis-flagged respondent (≥ 1 scales)”, a hover az `idno`-t (illetve `id_column` nélkül az 1-alapú sorszámot), a távolságot, a küszöböt és a két igen/nem mezőt mutatja, a tengelyfelirat tartalmazza a magyarázott varianciát, a felirat szövege megvan, a `pca_projection` kézzel számolt példán helyes komponenst, varianciaarányt és előjelet ad, nem elérhető és egyitemes skálánál üzenet jön ábra helyett
- [x] 3.3 Szintetikus eset m = 3 mellett (D5, D9): 4 Mahalanobis-skálás keret, amelyben az A válaszadó csak a vizsgált skálán kiugró, a B válaszadó három másik skálán igen, ezen nem; ellenőrzés: a teszt előbb a `score_run` pontozott tábláján igazolja, hogy A skálaszinten kiugró és nem jelölt, B jelölt és ezen a skálán nem kiugró, majd hogy a térképen A piros sima jelölővel, B szürke kiemelt jelölővel jelenik meg, és a jelmagyarázat „(≥ 3 scales)”
- [x] 3.4 `straightlining_heatmap(analysis, scored, rules, position)` (D6), a színek a `dataviz` skill szerint; ellenőrzés: tesztek az 1023-as válaszadóra (két sor, `Trust_Institutions` 5, `Satisfaction` 4 cella, ebben a sorrendben, z = validált értékek), az azonos értékek azonos színére (közös skála, rögzített zmin/zmax), és a straightlining nélküli válaszadóra (nincs ábra)
- [x] 3.5 `contradiction_details(analysis, rules, scored, position)` és az okok detektoronkénti csoportosítása (D7); ellenőrzés: teszt az 1026-os válaszadóra (`trstprt`, `trstplt` sorok a `Contradiction: trstprt>8 vs trstplt<2` címkével, `> 8`, `< 2` feltételek, a válaszadó értékei), és ellentmondás nélküli válaszadóra üres tábla
- [x] 3.6 `drilldown_options(scored, positions, id_column)` és `drilldown_index(options, chosen)` (D7); ellenőrzés: tesztek a címkékre (`1026 (score 33.33, suspicious)`, `1005 (score 66.67)`, pontszám nélküli sorra `N/A`), arra, hogy elérhető választásnál az index megmarad, kiszűrtnél 0, és üres opciólistára nincs index
- [x] 3.7 Teljesítménymérés: a 3.2 vetülete a valós ESS11 fájlon a `config/ess11.json` minden Mahalanobis-skálájára; ellenőrzés: az idő a PLANNING_LOG-ban, csak összesítő adat, válaszadói kimenet nem marad a repóban

## 4. `app.py` integráció

- [x] 4.1 `RunResult` új mezői (`scored`, `rules`, `analysis`, `flag_threshold`, `id_column`) a `run_surveyguard`-ban (D3); ellenőrzés: a meglévő `tests/test_app.py` és `tests/test_app_modular.py` módosítás nélkül zöld
- [x] 4.2 Megjelölt tábla egysoros kijelöléssel és a hőtérkép alatta (D6, D8), a kijelölés→pozíció segédfüggvénnyel, amely a szűrt táblát is kezeli; ellenőrzés: tiszta teszt a segédfüggvényre (szűretlen és „suspicious only” tábla), és a meglévő toggle-tesztek zöldek
- [x] 4.3 „Visual analytics” szakasz két füllel, a PCA-skálaválasztóval és a futáshoz kötött session-state gyorsítótárral (D5, D8); ellenőrzés: AppTest, hogy futás után van Plotly-ábra, a választó opciói a Mahalanobis-skálák rules-sorrendben, skálaváltás után a metrikák változatlanok, és bemenetváltáskor a gyorsítótár is törlődik
- [x] 4.4 „Respondent drill-down” szakasz (D7) a 3.6 függvényeivel, a megjelölt táblát szűrő ugyanazon maszkból képzett opciókkal; ellenőrzés: AppTest a fixture-ön: kikapcsolt szűrőnél az opciók `1026`, `1027`, `1032`, `1005`, `1021`, `1022`, `1023`, `1024`, `1033`, bekapcsoltnál `1026`, `1027`, `1032`, mindkét esetben egyezően a megjelenített tábla `Respondent` oszlopával; az `1023` kiválasztása után a szűrő bekapcsolása kivétel nélkül az `1026`-ra állítja a választót; az 1026 kiválasztásakor az ellentmondás-tábla két sora; választásváltás után a metrikák és a letöltések megmaradnak; bekapcsolt szűrő és gyanús nélküli bemenet mellett az üzenet, választó nélkül

## 5. Izoláció és regresszió

- [x] 5.1 CLI-importizoláció tesztje (D2): alfolyamatban a CLI futása után a `sys.modules`-ban nincs `plotly` és `surveyguard.visualization`; ellenőrzés: zöld, és szándékos piros futás egy ideiglenes `import surveyguard.visualization`-nel a `cli.py`-ban, majd visszaállítás
- [x] 5.2 Regresszió: a 1.2 fixture-futás hash-ei egyeznek; `git diff main -- surveyguard/scoring.py surveyguard/detectors.py surveyguard/reporting.py surveyguard/io.py surveyguard/config.py surveyguard/cli.py tests/test_fast_scoring.py` üres; `git diff --stat main -- tests/` csak új fájlokat mutat
- [x] 5.3 Teljes tesztfutás; ellenőrzés: `pytest -q` zöld, a darabszám = 358 + az új tesztek, és az idő a PLANNING_LOG-ban

## 6. Dokumentáció és ellenőrzés

- [x] 6.1 README: a webes felület szakasza a négy vizuális elemmel és az új függőségekkel; ellenőrzés: a leírt lépések egyeznek a felülettel
- [x] 6.2 `openspec validate add-visual-analytics-dashboard --strict`, `git diff --check` és `python -m compileall -q app.py surveyguard`; ellenőrzés: mind hibátlan
- [x] 6.3 Kézi böngészős ellenőrzés (`python -m streamlit run app.py`, `config/ess2.json` + valós ESS2 fájl): hisztogram a küszöbvonallal, PCA-térkép skálaváltással, sorkijelölés → hőtérkép, drill-down; ellenőrzés: a felhasználó elvégzi, az eredmény a PLANNING_LOG-ban

## 7. Javítások a kézi ellenőrzés után (ESS9, D10)

- [x] 7.1 Tengelyfeliratok: `automargin=True` és `title.standoff` minden ábra mindkét tengelyén, legalább `l=60`, `b=50` margó, a PCA jelmagyarázata az ábra fölött; ellenőrzés: teszt a hisztogram, a PCA-térkép és a hőtérkép layoutjára, és újra a 6.3 böngészős ellenőrzés
- [x] 7.2 A drill-down `Condition` cellája a teljes kifejezés (`trstprt > 8`); ellenőrzés: teszt mind az öt műveleti jelre, egy cella sem kezdődik `>` jellel, az AppTest a fixture-ön `trstprt > 8`, `trstplt < 2`
- [x] 7.3 Darabszám-felirat minden nem nulla hisztogram-oszlop fölött, helyet hagyó y-tengellyel; ellenőrzés: teszt a fixture-ön és az 1500 + 4 esetre (a nulla bineknek nincs felirata)
- [x] 7.4 Determinisztikus jitter a PCA-térkép kirajzolt koordinátáin (seed 0, legfeljebb a tengely szórásának 2%-a), jitter nélküli PC1/PC2 a hoverben, kiegészített felirat; ellenőrzés: tesztek a determinizmusra, a határra, a pontos hover-értékekre, az azonos pontok szétválására, és a piros pontok száma továbbra is = a skálatábla értéke
- [x] 7.5 Regresszió; ellenőrzés: `pytest -q` zöld (390 + az új tesztek), a meglévő tesztfájlok és a pontozó/CLI-modulok `git diff main`-je üres, a fixture CLI-hash-ei egyeznek a kiindulóval, `openspec validate add-visual-analytics-dashboard --strict` hibátlan

## 8. Hisztogram: log skála és piros gyanús bin-ek (második kézi ellenőrzés, ESS8, D4)

- [x] 8.1 `score_histogram(..., log_scale=False)`: log módban `type="log"`, `[log10(0.5), log10(max · 3)]` tartomány, „Respondents (log scale)” cím, egész tick-ek (1, 10, 100, 1000), nulla bin-ek oszlop és felirat nélkül; lineárisan a korábbi layout; ellenőrzés: tesztek az ESS8-alakú 3 / 165 / 1446 esetre és arra, hogy a lineáris ábra azonos a paraméter nélküli hívás eredményével
- [x] 8.2 Piros szín a teljesen a küszöb alatti bin-eken, kék a többin; ellenőrzés: teszt 50-es, 52-es (az 50–55 kék) és 60-as küszöbbel
- [x] 8.3 `histogram_caption`: a két szín megnevezése, a gyanúsak száma és aránya a pontozott táblából; ellenőrzés: teszt a 3 / 1614 → `0.19%` esetre, a fixture-re és az egyes számra
- [x] 8.4 `st.radio` („Y axis”, `Log` / `Linear`, vízszintes, alapból `Log`) a hisztogram fölött, a felirattal az ábra alatt; ellenőrzés: AppTest, hogy a radio alapból `Log`, az ábra log tengelyű, váltás után lineáris, és a metrikák és a megjelölt tábla megmaradnak
- [x] 8.5 Regresszió; ellenőrzés: `pytest -q` zöld, a meglévő tesztfájlok és a pontozó/CLI-modulok `git diff main`-je üres, `openspec validate add-visual-analytics-dashboard --strict` hibátlan

## 9. Apró megjelenítési javítások (D5, D6)

- [x] 9.1 Hőtérkép colorbar: fix 150 px hossz (`lenmode="pixels"`), legalább 300 px ábramagasság, tick csak az előforduló értékeken; ellenőrzés: teszt egy- és kétsoros hőtérképre (azonos hossz, a rajzterület elég magas, tick-ek = előforduló értékek) és egy 1, 2, 2, 5 válaszú esetre
- [x] 9.2 PCA jelmagyarázat: a két színes bejegyzés mindig kör, csak jelmagyarázatbeli nyomvonalakkal, a valódi pont-nyomvonalak `showlegend=False`; ellenőrzés: teszt a jelmagyarázat-bejegyzések nevére, formájára és színére, és hogy a fixture első piros pontja rombusz (ez okozta a hibát)
