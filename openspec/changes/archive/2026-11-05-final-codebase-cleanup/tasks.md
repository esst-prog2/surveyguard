## 1. A felülvizsgálat megismétlése a lezárandó állapoton

A proposal megállapításait az apply idején kell újra ellenőrizni. A feladatok nem módosítanak kódot; ha valamelyik találatot ad, az új információ: meg kell állni, és egyeztetni kell a felhasználóval.

- [x] 1.1 Bedrótozott útvonalak; ellenőrzés: `git grep -n -I -E "[A-Za-z]:[\\/]|/Users/|/home/|AppData" -- "*.py" requirements.txt` csak a `prepare_data.py` URL-jét és a `tests/test_visualization.py` `try:` / `except SystemExit as exc:` sorait adja (téves találatok), és a `git grep -n -E "\.sav|_HU_|weighted_raw" -- app.py detect_anomalies.py prepare_data.py run_spike.py "surveyguard/*.py"` csak az `io.py` 16. és 131. sorát
- [x] 1.2 scikit-learn; ellenőrzés: `git grep -n -i -E "sklearn|scikit" -- "*.py" requirements.txt` üres
- [x] 1.3 Streamlit-gyorsítótár; ellenőrzés: `git grep -n -E "st\.cache|cache_data|cache_resource" -- "*.py"` üres
- [x] 1.4 Tesztadatok; ellenőrzés: `git grep -n -E "ess_sav_files|_HU_|weighted_raw" -- tests` üres, és a `git grep -n "\.sav" -- tests` minden sora `tmp_path`-ban készülő fájl
- [x] 1.5 Nem használt importok; ellenőrzés: a `pyflakes` a scratchpadbe telepítve (`pip install --target`), a repó és a globális környezet érintése nélkül, hibát nem talál az `app.py`, a `detect_anomalies.py`, a `prepare_data.py`, a `run_spike.py`, a `surveyguard` és a `tests` kódján

## 2. Futtatás valós adat nélkül

- [x] 2.1 Friss klón a scratchpadbe (`git clone --single-branch`), ahol nincs `ess_sav_files/`; ellenőrzés: `python -m pytest -q` a klón gyökeréből 405 passed, és utána a `git status --short` üres
- [x] 2.2 Munkakönyvtár-függetlenség; ellenőrzés: egy üres mappából a klón `detect_anomalies.py`-ja lefut a fixture-ön (`Processed: 33`), és a klón `app.bundled_rules_files()` függvénye 13 fájlt ad

## 3. Lezárás

- [x] 3.1 A kód változatlansága; ellenőrzés: `git diff --stat main -- "*.py" requirements.txt config tests` üres
- [x] 3.2 A proposal „külön döntést igénylő” tételeinek állapota (helyi `.sav` ref-ek, archivált abszolút utak) a PLANNING_LOG-ban a felhasználó döntésével, vagy azzal, hogy nyitva maradnak; ellenőrzés: a sor a logban, és a `git ls-remote origin` tip-jei közül továbbra sem tartalmazza egyik sem a `2cadbfc` commitot
- [x] 3.3 Validálás; ellenőrzés: `openspec validate final-codebase-cleanup --strict` hibátlan
