## Why

A tanári visszajelzés szerint a demóleírásnak ki kell emelnie a sebességbeli fejlődést. A README 1. szakasza („The demo”) most csak annyit mond, hogy az eredmény „Within seconds” megjelenik, de azt nem, hogy ugyanez a futás korábban hány percig tartott. Egyetlen mondat a „Within seconds” mondat után ezt megmutatja.

## What Changes

### A beszúrandó mondat

Közvetlenül a „Within seconds, the "Overview" shows … 96.22.” mondat után, ugyanabba a bekezdésbe:

> Before the October speed-up, this exact run took 397 seconds, more than six and a half minutes.

A szakasz 5 mondatról 6-ra nő; a többi mondat szó szerint változatlan.

### Miért nem a példamondat („Two weeks ago, this exact process took 7.4 minutes.”)

- **A 7,4 perc más folyamat:** a 2026-10-25-i 444,8 s (7,4 perc) a régi kód **parancssoros** futása volt, részben tesztfutásokkal átfedve. A demó a **webes felületet** mutatja, ezt a régi kóddal korábban nem mértük pontosan.
- **Mérés most:** a gyorsítás előtti utolsó állapotot (`53543bd`) a scratchpadbe kicsomagolva, ugyanazzal a demóúttal (`.sav` feltöltése, beépített `config/ess2.json`, Run SurveyGuard) és ugyanazzal a valós `ESS2_HU_weighted_raw.sav` fájllal: **397,0 s** a Run gombtól az eredményig, azonos eredménnyel (1498 / 10 / 96.22). A mostani kód ugyanezen a gépen 8,4 s (2026-11-05-én 5,67 s), így a „Within seconds” igaz marad.
- **A „Two weeks ago” elavul:** a gyorsítás 2026-10-25-én került a `main`-be. A demó december 1-jén vagy 8-án lesz, akkor már öt-hat hete, ezért a mondat abszolút időt („the October speed-up”) használ.

## Capabilities

### New Capabilities

Nincs.

### Modified Capabilities

Nincs. Csak dokumentáció változik, ezért `skip_specs: true`.

## Impact

- **Változik:** a `README.md` 1. szakasza (egy mondattal bővül), a `PLANNING_LOG.md`, és ez az OpenSpec-változás.
- **Nem változik:** a README többi szakasza és a kód.
- **Canvas:** ha a Canvasba már beadott szövegnek egyeznie kell a README-vel, ott is frissíteni kell.
- **Adat:** a mondat csak egy időadatot tartalmaz; válaszadói adat és a régi kód másolata nem kerül a repóba.
