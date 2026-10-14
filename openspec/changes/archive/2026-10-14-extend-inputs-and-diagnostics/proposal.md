## Why

SurveyGuard jelenleg csak CSV-fájlokat tud közvetlenül betölteni, így az Excel- és SPSS-alapú felmérésekhez külön, hibalehetőségeket hordozó átalakítás szükséges. A futás eredményei jelenleg csak a konzolon jelennek meg, ami megnehezíti az automatizált archiválást és a detektorok eredményeinek áttekinthető megosztását.

## What Changes

- A fájlkiterjesztés alapján támogatottá válik a `.csv`, `.xlsx` és `.sav` közvetlen beolvasása.
- Az SPSS-bemenet mindig nyers numerikus kódokat ad a detektoroknak (`convert_categoricals=False`); nem támogatott kiterjesztés egyértelmű strukturális hibát eredményez.
- Az opcionális `--report <útvonal.md>` kapcsoló Markdown diagnosztikai riportot ír a futás feldolgozási és pontozási eredményeiből.
- A riport tartalmazza a feldolgozott és gyanús kitöltők számát, az átlagos és minimum `quality_score` értéket, a három detektor darabszámát és arányát, valamint a megjelölt kitöltők indoklásait.
- Az új formátumokhoz és a riporthoz determinisztikus unit- és CLI-tesztek készülnek.
- Az `openpyxl` és `pyreadstat` közvetlen függőségként, pontos `==` verzióval kerül a `requirements.txt` fájlba.

## Capabilities

### New Capabilities

### Modified Capabilities

- `survey-quality-detection`: a bemeneti formátumok, a sikeres futás összegzése és az opcionális Markdown diagnosztikai riport viselkedése bővül.

## Impact

- Érintett betöltési és CLI-réteg: `surveyguard/io.py`, `surveyguard/cli.py`.
- Érintett riportformázás: `surveyguard/reporting.py`.
- A meglévő pontozó és detektorlogika változatlan marad; a riport az előállított eredményoszlopokat fogyasztja.
- Függőségi, teszt- és dokumentációs frissítés szükséges.
