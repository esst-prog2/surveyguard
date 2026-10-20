## Why

A tanári kódvizsgálat a `surveyguard` csomagra terjedt ki, ezért két minőségi hiba kimaradt a csomagon kívüli előkészítő szkriptekből. A `run_spike.py` kalibrációs logikájának (`exact_five_percent_threshold`) nincs tesztje, pedig a README-ben dokumentált 5%-os Mahalanobis-küszöb ebből a függvényből származik. A `prepare_data.py` egy `except Exception` ággal minden hibát elnyel, és 0-s kilépési kóddal ér véget. Így egy sikertelen letöltés sikeres futásnak látszik, és a régi `spike_data.csv` észrevétlenül a helyén marad.

## What Changes

- Új tesztfájl a `run_spike.py` `exact_five_percent_threshold` függvényéhez, kézzel számolt konstansokkal:
  - `pd.Series(range(1, 21))` bemenetre a küszöb pontosan `19.5`;
  - ha a felső 5% határán a két legnagyobb érték azonos (mindkettő `20`), `ValueError` keletkezik;
  - ha a sorok száma túl kevés az 5%-os célhoz (kevesebb mint 20 érvényes érték), szintén `ValueError` keletkezik.
- A `prepare_data.py` modulszintű kódja egy `main() -> int` függvénybe kerül, a `detect_anomalies.py` / `surveyguard.cli` mintáját követve (`raise SystemExit(main())`). Így a szkript importálható és tesztelhető.
- Az `except Exception` ág megszűnik. Csak a várt hibatípusokat kapjuk el (hálózati hiba, sérült ZIP, fájlrendszer-hiba, hiányzó oszlop), ezekre egyértelmű hibaüzenet és **1-es kilépési kód** jár. Minden más kivétel traceback-kel, nem nulla kóddal állítja le a futást.
- A korábban csendes hibaesetek explicit hibát adnak: nincs CSV/TSV a ZIP-ben, vagy 1000-nél kevesebb teljes sor van.
- Offline, determinisztikus tesztek a `prepare_data.py` hibaágaira, a hálózati hívás helyettesítésével.

## Capabilities

### New Capabilities

- `spike-tooling`: a spike-adatok előkészítésének és a detektorkalibrációnak a megfigyelhető viselkedése. Ide tartozik a küszöbszámítás eredménye és hibái, valamint az előkészítő szkript kilépési kódja és kimeneti garanciái.

### Modified Capabilities

<!-- Nincs: a `survey-quality-detection` követelményei nem változnak. -->

## Impact

- Érintett kód: `prepare_data.py` (szerkezet és hibakezelés). A `run_spike.py` nem változik, csak tesztet kap.
- Új tesztek: `tests/test_spike_scripts.py`.
- A `surveyguard` csomag, a CLI, a detektorok és a pontozás változatlanok; függőségváltozás nincs.
- A `prepare_data.py` sikeres futásának kimenete (`spike_data.csv`, 1000 sor, `EXT1`–`EXT10`) változatlan.
