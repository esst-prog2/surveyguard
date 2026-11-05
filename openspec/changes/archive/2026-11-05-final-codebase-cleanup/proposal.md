## Why

A projekt lezárása előtt ellenőrizni kell, hogy a kódbázisban nem maradt-e bedrótozott útvonal, halott függőség, visszavont kódmaradvány, vagy valós adatra hivatkozó teszt. A felülvizsgálat 2026-11-05-én lefutott a `main` állapotán (aa34101): **a négy vizsgált területen nincs javítandó hiba, ezért ez a változás nem módosít kódot.** A változás a megállapításokat és a megismételhető ellenőrzést rögzíti, hogy az eredmény visszakövethető legyen.

## What Changes

### Megállapítások a négy vizsgált területen

| Terület | Eredmény | Bizonyíték |
|---|---|---|
| Bedrótozott útvonalak a produkciós kódban | **Nincs** | Nincs abszolút út és `.sav` fájlnév az `app.py`, a `detect_anomalies.py`, a `prepare_data.py`, a `run_spike.py` és a `surveyguard/*.py` fájlokban. A `.sav` csak támogatott kiterjesztésként szerepel (`io.py:16`, `io.py:131`). A `CONFIG_DIR` és a `DATA_PATH` a `__file__`-ból jön. A CLI és a `bundled_rules_files()` más munkakönyvtárból, friss klónból is működik. |
| scikit-learn / sklearn | **Nincs** | Nincs sem a `requirements.txt`-ben, sem a `visualization.py`-ban, sem más `.py` fájlban, és a `main` története szerint soha nem is volt (`git log -S`: 0 találat). Csak a döntést rögzítő archivált dokumentumok és a PLANNING_LOG említi. |
| `st.cache` / `st.cache_data` | **Nincs** | Nincs az `app.py`-ban, és a `main` története szerint soha nem is volt: a `st.cache_data` tervezéskor lett elvetve, kód nem készült hozzá. |
| Valós adatra hivatkozó tesztek | **Nincs** | A `tests/` nem hivatkozik az `ess_sav_files/` mappára; minden `.sav` a `tmp_path`-ban készül. Friss klónban, `ess_sav_files/` nélkül 405 teszt zöld, és a futás után a munkafa tiszta. |

További ellenőrzés: a `pyflakes` nem talált hibát (nincs nem használt import); a `requirements.txt` minden csomagja használatban van (az `openpyxl` a `pandas` motorjaként, a `pyreadstat` a `read_spss` mögött).

### Maradnak szándékosan

- **`RunResult.pca_cache`:** ez nem a visszavont gyorsítótár maradványa, hanem az elfogadott, futáshoz kötött megoldás (add-visual-analytics-dashboard, D5): a futással együtt törlődik, teszt rögzíti.
- **A README és a `.gitignore` hivatkozásai** az `ess_sav_files/` mappára: dokumentáció és adatvédelem, nem kód.
- **`spike_data.csv` és `config/` olvasása a tesztekben:** szó szerint nem „fixtures vagy tmp_path”, de ezek követett, a repóba tartozó fájlok, nem a `.gitignore` által védett adatok (a `spike_data.csv` nyilvános, anonimizált adat). Áthelyezésükhöz a `test_fast_scoring.py`-t is módosítani kellene.
- **Csak tesztek által használt függvények** (`load_csv`, `score_dataframe`) és a sehol nem olvasott `ScaleRun.required_rows` mező: a pontozó magban vannak, amelyet ez a változás nem érint.

### A kérésen kívül talált tételek (külön felhasználói döntést igényelnek, ez a változás nem nyúl hozzájuk)

1. **Valós `.sav` a helyi git-objektumok között.** A `2cadbfc` commit (2026-10-15, „Agent host session … baseline checkpoint”) tartalmazza az `ESS11_HU_weighted_raw.sav` fájlt (2 996 656 bájt). Csak a helyi `refs/agents/045f3515-…` ref-ek érik el (9 db). **Nincs a GitHubon:** a 29 távoli ref egyike sem tartalmazza, és egyetlen ág, távoli ág vagy tag sem éri el. Kockázat: egy `git push --mirror` feltöltené. A ref-ek törlése visszafordíthatatlan, és érintheti az agent host ellenőrzőpontjait.
2. **Helyi abszolút út két archivált dokumentumban.** A `2026-10-24-support-ess-modules-and-scale-aware-scoring/tasks.md` és a `2026-10-25-speed-up-spss-scoring/tasks.md` tartalmaz egy, a felhasználó helyi Letöltések mappájára mutató utat (a felhasználónévvel), és ez a GitHubon is látszik. Nem produkciós kód, és az archívum történeti rögzítés; a szöveg átírása nem távolítaná el a git-történetből.
3. **A tesztek a repó gyökeréből futnak.** Sok teszt munkakönyvtárhoz relatív utat használ, ezért a `tests/` mappából indítva elbuknak (pl. a `test_cli.py` 7 tesztje). A kérés a relatív utat megengedi, és a dokumentált futtatás a gyökérből történik.

## Capabilities

### New Capabilities

Nincs.

### Modified Capabilities

Nincs. A változás nem érint követelményt, ezért `skip_specs: true`.

## Impact

- **Kód, függőségek, tesztek, konfiguráció:** nem változik. A pontozó és a vizualizációs mag érintetlen.
- **Dokumentáció:** `PLANNING_LOG.md`, és ez az OpenSpec-változás.
- **Ág:** a meglévő `final-codebase-cleanup` (a `main`-nel azonos, aa34101).
