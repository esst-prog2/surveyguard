## Why

A README 1. szakasza („The demo”) a Homework 8 végleges demóleírása, és ezen a ponton lehet utoljára változtatni rajta. A mostani szöveg a félév eleji tervet írja le: terminálos futást kitalált fájlokkal és számokkal. A demó viszont a webes felületen, a valós ESS2 fájlon megy, képernyőképekkel, ezért a leírásnak ugyanezt az utat és a program valódi számait kell tartalmaznia. A README 2. és 3. szakasza ütközik az új leírással, ezért a felhasználó döntése szerint ezek érintett sorai is változnak.

## What Changes

### Ami a mostani szövegben már nem igaz

| Mostani szöveg | A `main` valódi állapota |
|---|---|
| Terminálban indul, `detect_anomalies.py` | A CLI működik, de a demó útja a webes felület (`python -m streamlit run app.py`) |
| `data/wave1_raw.csv`, `output/wave1_scored.csv` | Ilyen fájl és mappa nincs; a CLI a kimenetet a bemenet mellé írja |
| `config/scale_logic.json` | Ez a kétskálás minta; a demó a 22 skálás `config/ess2.json`-t használja |
| 2,500 válaszadó, 142 jelölt (80 / 42 / 20) | Kitalált számok; a valós ESS2-n 1498 válaszadó, 10 gyanús, 81 straightlining, 24 ellentmondás, 65 Mahalanobis |
| „Flagged 142 suspicious records. Main drivers: …” | A konzol nem ezt írja ki (`Processed: 1498`, `Suspicious: 10`, …) |
| Pontozott CSV megnyitása és rendezése | A demó nem ezt mutatja: a jelölt tábla már pontszám szerint rendezett, a letöltés a `_cleaned.csv` és a riport |

Ami továbbra is igaz: a `quality_score` és a `flag_reasons` oszlop létezik, de a demó útjához nem kell. A leírásból hiányzik minden, ami azóta készült: a webes felület, a beépített szabályfájlok, a vizuális analitika és a drill-down.

### Javasolt szöveg

A `README.md` `## 1. The demo` címe alatti bekezdés helyére, szó szerint:

> I run `python -m streamlit run app.py`, upload the real Hungarian survey file `ESS2_HU_weighted_raw.sav` in the sidebar, choose `config/ess2.json` from the "Bundled rules file" list, and click "Run SurveyGuard". Within seconds, the "Overview" shows 1,498 processed respondents, 10 of them suspicious (0.67%), and an average quality score of 96.22. Under "Visual analytics", the score histogram shows those 10 as a red bar left of the dashed threshold line at 50, and the "Mahalanobis PCA map" marks in red who stands out on the chosen scale. I select a suspicious respondent in the flagged table to see their straightlining heatmap, then choose the same person under "Respondent drill-down" to see their logical contradiction highlighted next to their actual answers. Finally, I download `ESS2_HU_weighted_raw_cleaned.csv`, which removes those 10 respondents and keeps the other 1,488, together with the report `ESS2_HU_weighted_raw_diagnostics.md`.

### A README 2. és 3. szakasza (a felhasználó döntése: az ellentmondás ne maradjon)

- **2. szakasz, felülírva:** az `in` sor a három bemeneti formátumot és a szabályfájl tartalmát nevezi meg; az `out` sor a webes és a parancssoros kimenetet; az `in between` sor a tényleges, explicit ellentmondás-szabályokat a korábbi „reversed items” helyett.
- **3. szakasz, törölve:** a „NOT do this term” listáról a grafikus felület sora, mert a program már tartalmazza.
- **3. szakasz, felülírva:** az „Automated deletion” sor pontosítva: a forrásadatot a program nem törli, a tisztított CSV külön fájl, amelyet a kutató választ.

### Ellenőrzött adatok

A szöveg minden száma és felirata a program mostani futásából jön (`main`, aa34101), a demó útját az `app.py`-n végigvezetve a valós `ESS2_HU_weighted_raw.sav` fájllal: 1498 feldolgozott és 10 gyanús válaszadó (0,67%), 96.22 átlagpontszám, 5,67 s a Run gombtól az eredményig, 22 skála, a hisztogramon 10 fő a 30–35-ös binben, 10 eltávolított és 1488 megtartott válaszadó, a két letölthető fájl neve. A CLI ugyanezeket a számokat adja.

## Capabilities

### New Capabilities

Nincs.

### Modified Capabilities

Nincs. Csak dokumentáció változik, ezért `skip_specs: true`.

## Impact

- **Változik:** a `README.md` 1. szakasza, a 2. szakasz három sora, a 3. szakasz két sora, a `PLANNING_LOG.md`, és ez az OpenSpec-változás.
- **Nem változik:** a README többi szakasza és a kód.
- **Adat:** a szöveg csak összesítő számokat és fájlneveket tartalmaz, válaszadói adatot nem; a valós `.sav` továbbra sem kerül a repóba.
- **A demóval nem ütköző, ezért nem javított eltérések:** a 4. szakasz `Straightlining_Error` jelölése a programban `Straightlining_<skála>`; az 5. szakasz jövő idejű tervei a félév eleji állapotot írják le; a 6. szakasz a tanár visszajelzése, azt nem szabad átírni.
