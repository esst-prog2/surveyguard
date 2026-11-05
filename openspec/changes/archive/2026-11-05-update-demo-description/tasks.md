## 1. A szöveg

- [x] 1.1 A felhasználó jóváhagyja a proposal javasolt szövegét; ellenőrzés: a jóváhagyás a PLANNING_LOG-ban
- [x] 1.2 A `README.md` `## 1. The demo` szakaszának cseréje a jóváhagyott szövegre; ellenőrzés: a szakasz szó szerint egyezik a proposal szövegével, a kód `git diff main`-je üres
- [x] 1.3 A 2. és 3. szakasz ellentmondásainak feloldása a felhasználó döntése szerint; ellenőrzés: a `git diff main -- README.md` csak az 1. szakaszt, a 2. szakasz három sorát és a 3. szakasz két sorát érinti

## 2. Lezárás

- [x] 2.1 Validálás és adatvédelem; ellenőrzés: `openspec validate --strict` hibátlan, a commitban nincs `.sav`, `ess_valtozas.txt` és `program_osszefoglalo.txt`
- [x] 2.2 Commit, push, PR a `main`-be; ellenőrzés: a PR URL-je és a commit hash-e a PLANNING_LOG-ban
- [x] 2.3 A végleges szöveg átadása a Canvashoz; ellenőrzés: a kiadott szöveg szó szerint egyezik a README 1. szakaszával a `main`-re szánt commitban
