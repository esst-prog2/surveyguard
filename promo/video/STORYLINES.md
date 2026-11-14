# SurveyGuard promo film: three storylines (HyperFrames, story.md §2)

Source: `docs/index.html` (live at https://esst-prog2.github.io/surveyguard/), `PRODUCT.md`, README demo. Facts only from these: 1,498 respondents, 10 suspicious (0.67%), 8.4 s vs. 397 s, ESS 1 to 11 rules, 66.7 stays in / 33.3 suspicious, the four real charts in `docs/img/`.

The one thing to remember: "It found the people who didn't read, and told me why."
The spine: one survey file travels from "1,498 rows nobody can check by eye" to "10 suspicious, each with a reason".

Assumptions for all three: 28 to 32 s, 1920×1080 at 30 fps, no voiceover, English on-screen text. Sound: no free local music generator is installed (MusicGen is optional and missing), so the default is quiet sound design made locally (soft ticks on rows, one low hit on the payoff); HeyGen catalog music would need a HeyGen account. Look: the page's own brand world (warm paper, Source Serif 4, IBM Plex, red only for "suspicious"); HyperFrames' spec bans the cream-paper-serif look as a *default*, but here it is the brand's own, so the brief wins.

---

## A. "Spot the one who didn't read" (recommended: it is built from real assets we already have and continues the page's own hero)

- **Device / form:** the feature as the hook / one frame that rebuilds. The answer grid from the page's hero never leaves the frame; it keeps rearranging into each real chart.
- **What the viewer sees and feels:** a grid of survey answers fills row by row, one row goes flat and gets a red outline, and the viewer gets it before reading a word. The same grid grows to 1,498 rows, and SurveyGuard turns it into a short list with reasons.
- **First two seconds:** frame 0 is the grid half-filled (six trust items as column labels); rows drop in with soft ticks; at 1.5 s row 1044 lands as one flat colour and a red outline draws around it.
- **Beats:** hook (grid, the flat row, 0 to 3 s) → tension (the grid multiplies to 1,498 rows, too many to check by eye, 3 to 6 s) → reveal ("SurveyGuard" as a title, 6 to 8 s) → proof, three verbs, each a real chart from `docs/img/`: *flat* (the straightlining heatmap), *contradicts* (the drill-down table), *stands out* (the PCA map) (8 to 19 s) → payoff (the score histogram builds; 1,498 becomes 10 suspicious; the 66.7 / 33.3 ledger: "One flag is a warning, not a verdict", 19 to 25 s) → claim ("Every flag says why", 25 to 27 s) → end card (SurveyGuard wordmark wipes in, "Try it in 4 steps", esst-prog2.github.io/surveyguard, 27 to 30 s).
- **Look:** warm paper ground, Source Serif 4 titles, IBM Plex Sans text, blue answer cells, the page's red used only for the flat row, the suspicious bar, and "suspicious".
- **Sound:** a tick per row landing, a soft swell as the grid multiplies, one low hit when 1,498 becomes 10, silence under the end card.

## B. "One number lands" (the bold one)

- **Device / form:** a number lands / cut on the beat. Giant kinetic type and colour fields; every cut lands on a beat.
- **What the viewer sees and feels:** numbers carry the argument, each earned by a short scene: 1,498 answers, 10 who didn't read, 397 s that became 8.4 s, 11 ESS rounds ready to use. Confident and fast.
- **First two seconds:** "1,498" fills the frame in Source Serif; on the beat it splits into 1,498 tiny cells, and ten of them flash red.
- **Beats:** hook (1,498 → cells, ten red) → tension ("which ten?", the cells blur by) → reveal (SurveyGuard) → proof (three verbs, each with a real chart behind the type: flat, contradicts, stands out) → payoff ("397 s" struck through, "8.4 s" slams in; then "10 suspicious, 0.67%") → claim ("One flag is a warning, not a verdict") → end card.
- **Look:** full-bleed colour fields from the page's palette (paper, blue, one red field), type at 300 to 500 px, hard cuts.
- **Sound:** needs a beat to cut to; without a free music source here, a built metronome-like pulse; best with a real track (HeyGen catalog, account needed).

## C. "Before and after"

- **Device / form:** life before and after / split screen to one.
- **What the viewer sees and feels:** the left pane is the old way: a researcher scrolling a 1,498-row spreadsheet, squinting, highlighting rows by hand, the clock running. The right pane is SurveyGuard: upload, run, report. The left pane collapses into the right one.
- **First two seconds:** split screen; left, an endless spreadsheet scroll with a timer counting; right, an empty upload box.
- **Beats:** hook (split) → tension (left keeps churning) → reveal (right pane: SurveyGuard, Run) → proof (upload, run, the three real charts populate) → payoff (left collapses; "10 suspicious, each with a reason") → claim → end card.
- **Look:** the left pane in grey spreadsheet tones, the right in the brand world; red only on the suspicious.
- **Sound:** keyboard and mouse clicks on the left, quiet on the right, one hit on the collapse.
- **Needs from you:** real screens of the Streamlit app (upload, Run, Overview) that I cannot capture headless; without them they would be labelled placeholders.
