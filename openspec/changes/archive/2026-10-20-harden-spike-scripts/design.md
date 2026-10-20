## Context

A motivációt lásd a proposal.md „Why” részében. Jelenlegi állapot:

- `run_spike.py`: az `exact_five_percent_threshold` tiszta függvény, a `main()` az `if __name__ == "__main__"` mögött van, ezért a modul mellékhatás nélkül importálható. Tesztje nincs.
- `prepare_data.py`: minden kód modulszinten fut, így importáláskor azonnal letölt. Egyetlen `except Exception` ág van, amely csak kiír egy üzenetet, ezért a kilépési kód 0. A `[...][0]` CSV-keresés üres listára `IndexError`-t dob, ezt is az általános ág nyeli el. A `head(1000)` szó nélkül kevesebb sort is visszaadhat.
- A `surveyguard` hibakezelési mintája (`surveyguard/cli.py`, `detect_anomalies.py`): a `main()` `int`-et ad vissza, csak a várt hibacsaládot (`SurveyGuardError`) kapja el, `Error: ...` üzenetet ír, `1`-gyel tér vissza, a belépési pont pedig `raise SystemExit(main())`. A tesztek `python -m pytest` alatt futnak, így a gyökérkönyvtári modulok (`run_spike`, `prepare_data`) importálhatók.

## Goals / Non-Goals

**Goals:**
- A kalibrációs függvény mindhárom ágának (eredmény, holtverseny, kis minta) determinisztikus lefedése kézzel számolt konstansokkal.
- A `prepare_data.py` kilépési kódja megbízhatóan jelezze a sikert vagy a hibát, és ez hálózat nélkül tesztelhető legyen.

**Non-Goals:**
- A `run_spike.py` logikájának módosítása (csak tesztet kap).
- A letöltési URL, a kimeneti fájlnév vagy a kimeneti útvonal (cwd-relatív) megváltoztatása.
- A `prepare_data.py` beemelése a `surveyguard` csomagba vagy a `SurveyGuardError` hierarchia használata. A szkript a csomagon kívül marad, és nem függ tőle.
- Újrapróbálkozás vagy timeout-politika a letöltésre.

## Decisions

1. **`main() -> int` + `raise SystemExit(main())` a `prepare_data.py`-ban.** Ez a `detect_anomalies.py` mintája. Importálhatóvá teszi a szkriptet, és a teszt közvetlenül ellenőrizheti a visszatérési kódot.
   *Alternatíva:* `sys.exit(1)` közvetlenül az `except` ágban. Elvetettük, mert a függvény közepén kilépni nehezebben tesztelhető, és eltér a projekt mintájától.
   *Alternatíva:* sima `raise` az `except` ágban. Ez is nem nulla kódot adna, de a felhasználó várt hibákra (pl. nincs hálózat) traceback-et kapna egy egysoros üzenet helyett.

2. **Szűk `except` a várt hibákra, minden más propagál.** Elkapjuk az `urllib.error.URLError`-t (a `HTTPError` is ide tartozik), a `zipfile.BadZipFile`-t, az `OSError`-t és a `pandas.errors.ParserError`-t, valamint egy szkripten belüli `PreparationError(Exception)`-t az általunk felismert tartalmi hibákra. Ezekre `Error: ...` üzenet megy a stderr-re, és a visszatérési kód `1`. Az `except Exception` megszűnik, ahogy a `surveyguard` auditjában is (lásd PLANNING_LOG, 2026-10-13).
   *Alternatíva:* `except Exception` + `return 1`. Ez is nem nulla kódot adna, de programozási hibákat is elfedne.

3. **A korábban implicit hibák explicit ellenőrzést kapnak.**
   - Ha a ZIP-ben nincs `.csv`/`.tsv`, `PreparationError` keletkezik (a mostani `IndexError` helyett).
   - Hiányzó `EXT1`–`EXT10` oszlop esetén a `PreparationError` felsorolja a hiányzó oszlopokat (a mostani `KeyError` helyett).
   - Ha 1000-nél kevesebb a teljes sor, `PreparationError` keletkezik a tényleges sorszámmal, írás nélkül.
   Az írás az utolsó lépés marad, így hiba esetén a meglévő `spike_data.csv` érintetlen.

4. **Az üzenetek a stderr-re mennek.** A `surveyguard.cli` stdout-ra ír, de a szkript esetében a stderr a helyes csatorna. A tesztek a `capsys`-szel a stderr-t ellenőrzik. A sikeres futás üzenetei maradnak a stdout-on.

5. **Tesztek a `tests/test_spike_scripts.py` fájlban, `monkeypatch`-csel.** A `prepare_data` tesztjei a `urllib.request.urlopen`-t cserélik le: egy hívás `URLError`-t dob, a többi memóriában épített ZIP-et ad vissza (rossz bájtok; ZIP CSV nélkül; hiányzó oszlop; 999 teljes sor; 1000 teljes sor). A kimenet a `tmp_path`-ba kerül, ehhez a teszt a `monkeypatch.chdir`-t használja, mert a kimeneti útvonal cwd-relatív marad. A kalibrációs teszt pontos egyenlőséget (`== 19.5`) vár, mert az eredmény bináris lebegőpontosan is pontos.

## Risks / Trade-offs

- [A szűk `except` lista kihagyhat egy valós, várt hibatípust, ami így traceback-kel áll le.] → Ez elfogadható: a kód így is nem nulla, tehát a hiba nem rejtőzik el. Ha új hibatípus jelenik meg, felvehető a listára.
- [A `monkeypatch`-elt `urlopen` nem ellenőrzi a valódi szervert.] → A valódi letöltés kézi ellenőrzés marad (tasks 3.2), a CI-tesztek hálózatfüggetlenek maradnak.
- [A 1000 soros minimum szigorúbb a jelenlegi viselkedésnél.] → Szándékos: a `run_spike.py` és a README 1000 kitöltőre kalibrált eredményeket közöl.
