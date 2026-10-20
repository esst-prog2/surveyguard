## 1. Kalibrációs unit tesztek (`run_spike.py`)

- [x] 1.1 Hozd létre a `tests/test_spike_scripts.py` fájlt egy teszttel, amely `pd.Series(range(1, 21))` bemenetre pontosan `19.5`-öt vár (`== 19.5`), és ugyanezt egy hozzáfűzött `NaN` mellett is. Ellenőrzés: `python -m pytest -q tests/test_spike_scripts.py` zöld.
- [x] 1.2 Adj hozzá holtverseny-tesztet: a `pd.Series(list(range(1, 19)) + [20, 20])` bemenet `pytest.raises(ValueError, match="exact 5% threshold impossible")` alatt fusson. Ellenőrzés: a teszt zöld, és a `run_spike.py` változatlan (`git diff --stat run_spike.py` üres).
- [x] 1.3 Adj hozzá kis minta tesztet: `pd.Series(range(1, 20))` (19 érték) esetén `ValueError` jön, `match="enough rows for a 5% target"`. Ellenőrzés: a teszt zöld.

## 2. Szigorú hibakezelés (`prepare_data.py`)

- [x] 2.1 Tedd a modulszintű kódot egy `main() -> int` függvénybe, a belépési pont legyen `if __name__ == "__main__": raise SystemExit(main())`. Ellenőrzés: `python -c "import prepare_data"` hálózati hívás és kimenet nélkül fut le.
- [x] 2.2 Vezesd be a szkripten belüli `PreparationError` kivételt. Ezt dobja a kód, ha a ZIP-ben nincs `.csv`/`.tsv` fájl, ha hiányzik valamelyik `EXT1`–`EXT10` oszlop (a hiányzókat fel kell sorolni), és ha 1000-nél kevesebb a teljes sor (a tényleges darabszámmal). A fájlírás maradjon az utolsó lépés. Ellenőrzés: a 2.4 hibaág-tesztjei zöldek.
- [x] 2.3 Cseréld le az `except Exception` ágat szűk `except`-re (`urllib.error.URLError`, `zipfile.BadZipFile`, `OSError`, `pandas.errors.ParserError`, `PreparationError`). Ezekre `Error: ...` üzenet menjen a stderr-re, és a függvény `1`-et adjon vissza; siker esetén `0`-t. Ellenőrzés: `grep -n "except Exception" prepare_data.py` üres.
- [x] 2.4 A `tests/test_spike_scripts.py`-ban `monkeypatch`-elt `urllib.request.urlopen`-nel és `monkeypatch.chdir(tmp_path)`-szal teszteld a következő eseteket: hálózati hiba, nem ZIP tartalom, ZIP CSV nélkül, hiányzó oszlop, 999 teljes sor. Mindegyiknél `main() == 1` legyen, a stderr tartalmazza az `Error:` üzenetet, és ne jöjjön létre `spike_data.csv`. Ellenőrzés: a tesztek zöldek, hálózat nélkül is.
- [x] 2.5 Teszteld a nem várt hibát: egy `urlopen`, amely `RuntimeError`-t dob, propagáljon (`pytest.raises(RuntimeError)`). Ellenőrzés: a teszt zöld.
- [x] 2.6 Teszteld a sikeres esetet: egy 1000-nél több teljes sort és egy NaN-os sort tartalmazó TSV-ZIP után `main() == 0` legyen, a `spike_data.csv` pedig pontosan 1000 sort és `EXT1`–`EXT10` oszlopokat tartalmazzon. Ellenőrzés: a teszt zöld.

## 3. Teljes ellenőrzés és dokumentálás

- [x] 3.1 Futtasd: `python -m pytest -q` (a teljes csomag zöld, a meglévő tesztek száma nem csökken), `python -m compileall -q surveyguard detect_anomalies.py run_spike.py prepare_data.py` és `git diff --check`. Az eredményt rögzítsd a `PLANNING_LOG.md`-ben.
- [x] 3.2 Kézi ellenőrzés: egy elérhetetlen URL-re mutató futtatásnál a `python prepare_data.py; echo $?` eredménye `1` legyen. Ha van hálózat, egy valódi futtatás `0`-t és 1000 soros kimenetet adjon; utána állítsd vissza a `spike_data.csv`-t (`git diff --stat spike_data.csv` üres). Az eredményt rögzítsd a `PLANNING_LOG.md`-ben.
- [x] 3.3 Validáld a change-et: `openspec validate harden-spike-scripts --strict` hibamentes.
