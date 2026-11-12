# SurveyGuard promo page: critique (Impeccable `critique`, simulated)

Page under review: `promo/variant-a-paper.html` (variant A with B's hero animation), as approved on 2026-11-12.

## Through three pairs of eyes

### A classmate (knows the course, not the project)
- Gets the idea from the hero figure in a few seconds; the single-colour row is the strongest part of the page.
- The column labels in the figure (`prl`, `lgl`, `plc`, `plt`, `prt`, `ep`) mean nothing to them; they read as decoration, which is acceptable for a figure whose point is the colour pattern.
- Would try it, and would get stuck at the same place as the stranger (see below).

### My teacher (knows the project and its history)
- Recognises the real numbers (1,498 / 10 / 8.4 s vs. 397 s) from the README demo; nothing is invented, and red is only used for "suspicious".
- "8.4 s" has no context about the machine; "vectorised rewrite" is jargon for a non-programmer reader. Both are minor.
- Would check whether the instructions actually work from scratch, as the README demo was checked from a fresh clone.

### A stranger (lands on the page from a link, has nothing installed)
- Understands what it is for and who it is for.
- Then follows "How to try it" literally, and it breaks at every step:
  1. `python -m pip install -r requirements.txt` fails: they have no `requirements.txt`, because the page never says to get the code. The "Try it in 3 commands" button promises something the page does not deliver.
  2. Step 3 tells them to upload a survey file and choose `config/ess2.json`, but they have no survey file. The real Hungarian ESS file behind the 1,498 figure is not in the repository (`ess_sav_files/` is in `.gitignore`).
  3. The command-line alternative uses `data.sav`, a file that does not exist.

## Weakest part

**"How to try it" is not followable by the people the page is written for.** It silently assumes the reader already has the repository and a survey file. Every other weakness is cosmetic; this one makes the page's main call to action ("Try it in 3 commands") fail for a newcomer.

## Fix (applied in `promo/variant-a-paper.html`)

1. New first step: get the code with `git clone https://github.com/esst-prog2/surveyguard.git` and `cd surveyguard` (two lines, no `&&`, so it also works in Windows PowerShell 5.1). Now the page really has three commands: clone, install, start.
2. Step 3 now names a file that is in the repository: the synthetic `tests/fixtures/ess2_mock.csv` with the bundled `config/ess2.json`, and says what to expect (284 respondents, 8 suspicious, checked with the CLI on 2026-11-12). Own `.csv`, `.xlsx`, or `.sav` files remain the main path.
3. The command-line alternative uses the same real file and an explicit `--output`, so it runs as written after the clone.

4. Found while checking the fix at 360 px: the same section was wider than a phone screen, because the long commands widened the steps' grid column; the Copy buttons were off-screen. Fixed with `min-width: 0` on the step content, so each command scrolls inside its own block.

Checked: a fresh `git clone` of the public repository into a temporary folder contains `requirements.txt`, `app.py`, `tests/fixtures/ess2_mock.csv`, and `config/ess2.json`, and the page's command-line example runs there as written (`Processed: 284`, `Suspicious: 8`); `pip install` was not re-run, as the dependencies were already installed. The section was re-checked in headless Edge at 360 px.

## Left as is (minor, noted for later)
- No machine context next to "8.4 s".
- "vectorised rewrite" could become "rewrite" for non-programmers.
- Cryptic item codes in the hero figure.

## Follow-up (2026-11-12, after the user's feedback)
- The item codes in the hero figure are replaced by full names (Parliament, Legal system, Police, Politicians, Parties, EU Parliament), set vertically above the columns, with the title "Trust in … (answers from 0 to 10)"; checked at 1280 px and 360 px.
- No machine context for "8.4 s" and the word "vectorised" stay as they are, by the user's decision.
