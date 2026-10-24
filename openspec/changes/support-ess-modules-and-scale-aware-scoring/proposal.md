## Why

A SurveyGuard most két ESS-skálát figyel (`Trust_Institutions`, `Satisfaction`) egyetlen szabályfájlból. Egy ESS-kör viszont állandó (core) és rotáló modulokból áll, több tucat skálával, skálatípusonként eltérő hiánykódokkal és szűrt blokkokkal. Ráadásul a mostani „bármelyik skálán jelez → büntetés 1” logika a skálák számával gyorsan növeli a téves jelöléseket: k független skálánál kb. 1−0,95^k arányban jelöl (10 skálánál ~40%, 20-nál ~64%). A valós ESS2 HU adaton (1498 válaszadó) 28 jelölt skálán, alpha 0,05 mellett a válaszadók 72,7%-a kapna Mahalanobis-jelölést. Ahhoz, hogy egy teljes ESS-kört értelmesen lehessen elemezni, moduláris konfiguráció és skálaszám-tudatos pontozás kell.

## What Changes

- **Moduláris szabályfájlok:**
  - új, opcionális `include` lista, az útvonalak a beemelő fájlhoz képest relatívak;
  - a körkörös vagy ismételt include konfigurációs hiba;
  - a meglévő validáció (egyedi skálanév, egy oszlop egy skálában, a missing kód a tartományon kívül) az összefésült konfigurációra fut, ütközésnél mindkét fájlt megnevezve.
- **Új skálaszintű mezők:**
  - `module` (`"core"` | `"rotating"`, csak a riporthoz és a dokumentációhoz);
  - `required` (alapértéke `true`). Egy `false` skála, amelynek az összes oszlopa hiányzik, kimarad, és a CLI-összefoglaló meg a riport név szerint felsorolja. Ha csak az oszlopai egy része hiányzik, az hiba.
  - `detectors` (alapértéke `["straightlining", "mahalanobis_outlier"]`);
  - `min_items_straightlining` (alapértelmezett minimum nincs);
  - `mahalanobis_min_rows_per_item` (alapértéke 0, ilyenkor marad a mostani legalább 2 soros feltétel).
- **Alpha alapú Mahalanobis-küszöb:** skálánként pontosan egy adható meg, `mahalanobis_threshold` vagy `mahalanobis_alpha`. Alpha esetén a küszöb a khí-négyzet-eloszlás (1−alpha)-kvantilise, ahol a szabadsági fok az itemszám (`scipy.stats.chi2.ppf`). Ha mindkettő szerepel, az validációs hiba. A Mahalanobis detektor nélküli skálán egyik sem adható meg.
- **Rule-only változók:** új, opcionális `variables` szakasz bináris, kategoriális, darabszám- és évszám-változóknak (`valid_min`, `valid_max`, `missing_codes`, `module`, `required`). Ezek csak ellentmondás-szabályban szerepelhetnek, detektor nem fut rajtuk, és nem kapnak `data_quality` jelölést.
- **Skálaszám-tudatos Mahalanobis-jelölés:**
  - új gyökérszintű kulcs: `mahalanobis_min_scales` (m), pozitív egész, alapértéke 1, ami a mai viselkedés; beemelt fájlban hiba;
  - a Mahalanobis detektor csak akkor jelez (`mahalanobis_outlier_triggered`, `Mahalanobis_<skála>` okok a `flag_reasons`-ban), ha a válaszadó legalább m skálán kiugró;
  - m alatt a skálánkénti jelzések a `detector_details`-ben, a távolságoszlopokban és a riport skálatáblázatában látszanak;
  - mindhárom detektor büntetése 0/1 marad, a pontszámképlet nem változik;
  - a straightlining téves riasztásait a `min_items_straightlining` és a skálánkénti `detectors` kezeli, az ellentmondás-detektor változatlan;
  - nincsenek új `*_penalty` oszlopok.
- **Riport, CLI és GUI:**
  - a riport új „Scale results” szakaszt kap: skálánként modul, itemszám, detektorok, küszöb és annak forrása, érvényes sorok, straightlining-jelölések, skálaszintű Mahalanobis-jelölések, státusz; a detektortáblázat Mahalanobis-száma az m-küszöböt elérő válaszadóké, az m értékével feliratozva;
  - új „Skipped scales and rules” szakasz is kerül a riportba;
  - a CLI-összefoglaló csak akkor kap „Skipped scales: …” sort, ha kimaradt skála;
  - a GUI-ban skálatáblázat jelenik meg, és a rules feltöltés mellett egy beépítettkonfig-választó (`config/*.json`). Egy include-ot tartalmazó feltöltött rules fájl világos hibát ad.
- **ESS-konfigurációk:**
  - `config/ess/core.json`, `config/ess/r2_health.json`, `config/ess/r2_econ_morality.json` és `config/ess/r2_family_work.json`, ezeket mind a `config/ess2.json` emeli be;
  - 22 attitűdskála, a kódokat a valós `.sav` metaadataiból ellenőriztük;
  - alpha 0,01, `min_items_straightlining` 5 és `mahalanobis_min_rows_per_item` 10; a gyökérben `mahalanobis_min_scales` 3 és `flag_threshold` 50;
  - konzervatív, blokkokon átívelő ellentmondás-szabályok (ellentétes attitűdpárok és szociodemográfiai konzisztencia), mindegyik hangolható heurisztikaként jelölve.
- A `config/scale_logic.json` és a `config/spike_logic.json` nem változik; a `flag_threshold` mindenhol 50 marad.
- A spike-regresszió és az ess_mock eredményei változatlanok:
  - a spike CLI-összefoglalója és pontozott CSV-je bájtra azonos (1000 / 2 / 181 / 20 / 140 / 47 / 0 / 13 / 13 / 96.61 / 0.00);
  - a `run_spike.py` kimenete és a 50 Mahalanobis-outlier nem változik;
  - az ess_mock: 33 / 3 / 9 / 4 / 4 / 4 / 2 / 2 / 0 / 87.88 / 33.33, gyanús: 1026, 1027, 1032;
  - csak a riport kap új szakaszokat, ezért új referencia-hash-eket rögzítünk.
- A SciPy újra függőség lesz: `scipy==1.15.3` Python 3.10-re, `scipy==1.17.1` Python 3.11+-ra.
- Új szintetikus fixture-ök: include-lánc, körkörös include, ütköző skálák és oszlopok, hiányzó rotáló modul, részben hiányzó oszlopok, `min_items_straightlining`, alpha-küszöb, minimális sorszám és a `mahalanobis_min_scales` legalább három skálával. A tesztszám nem csökkenhet 91 alá.
- README: új szakasz a moduláris ESS-konfigurációról és a `mahalanobis_min_scales` küszöbről.

## Capabilities

### New Capabilities

<!-- Nincs új capability. -->

### Modified Capabilities

- `survey-quality-detection`:
  - `include`-alapú moduláris szabályfájlok és rule-only `variables`;
  - skálaszintű `module`/`required`/`detectors`/`min_items_straightlining`/`mahalanobis_min_rows_per_item`/`mahalanobis_alpha`;
  - gyökérszintű `mahalanobis_min_scales` (a Mahalanobis csak legalább m skálán jelezve triggerel);
  - skálánkénti eredmények és kihagyott skálák a riportban és az összefoglalóban;
  - moduláris ESS2-konfigurációk.
- `web-interface`: beépítettkonfig-választó a rules feltöltés mellett, include-os feltöltés elutasítása, skálatáblázat és kihagyott skálák az eredmények között.
- `spike-tooling`: a spike-regresszió követelménye pontosítva: az összefoglaló és a pontozott CSV bájtra azonos, csak a riport kap új szakaszokat.

## Impact

- **Kód:**
  - `surveyguard/config.py`: include-feloldás, összefésülés, új mezők, `variables`, alpha → küszöb, `mahalanobis_min_scales`;
  - `surveyguard/io.py`: oszlopellenőrzés `required`-del, kihagyott skálák;
  - `surveyguard/detectors.py`: skálánkénti detektorlista, `min_items_straightlining`, minimális sorszám;
  - `surveyguard/scoring.py`: futási metaadat skálánként, az m-küszöbös Mahalanobis-trigger;
  - `surveyguard/reporting.py`: „Scale results” és „Skipped” szakaszok, feltételes „Skipped scales” sor;
  - `surveyguard/cli.py`;
  - `app.py`: beépítettkonfig-választó, skálatáblázat.
  - A `run_spike.py` nem változik.
- **Konfiguráció:** új `config/ess2.json` és `config/ess/*.json`; a meglévő konfigurációk nem változnak.
- **Függőség:** a `requirements.txt` újra tartalmazza a SciPy-t.
- **Tesztek:** új tesztek és fixture-ök a `tests/` alatt. A meglévő tesztek várt számai nem változnak; csak a GUI-tesztek sidebar-választása módosul (a „Rules source” feltöltés opciója).
- **Adat:** az `ESS2_HU_weighted.sav` csak olvasásra és metaadat-ellenőrzésre kell, és a repóba nem kerül.
- **Dokumentáció:** README és `PLANNING_LOG.md`.
