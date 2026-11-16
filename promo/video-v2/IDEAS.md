# SurveyGuard video, second version: three ideas

Brief (Canvas, Homework 10 and "Look what you built"): about 30 seconds, for someone who has never heard of SurveyGuard; it goes on the page; it should add something the page can't, not retell it (a compelling use case, a before and after, a short story, or the app at its best); real screens and results for what the program already does, anything it doesn't do yet clearly marked; it must work without sound.

Facts used (from README.md, docs/index.html, app.py): the Streamlit app takes a `.csv`, `.xlsx`, or `.sav` file and a bundled rules file (ESS 1 to 11), "Run SurveyGuard" shows processed / suspicious / average score, detector results, the flagged respondents table, the straightlining heatmap, the score histogram, the Mahalanobis PCA map, the respondent drill-down, and downloads a diagnostic report and a cleaned CSV. Real demo: Hungarian ESS round 2, 1,498 respondents, 10 suspicious, 8.4 s.

What the page already shows: the idea (an answer grid with a straightliner), the numbers, the three detectors, four chart screenshots, how to install. What it never shows: the app itself, a person using it, and what happens to their work.

---

## 1. "The night before the deadline" (a short story; recommended, it is the user's own idea)

An animated social science student sits at her desk with 1,498 survey answers and a thesis chapter due tomorrow; she suspects some respondents just clicked through. She opens SurveyGuard, and from here the screen is the real app: she uploads the file, clicks Run, the Overview shows 10 suspicious, a click on one flagged respondent shows their flat answers and the broken rule, and she downloads the cleaned file and the report and finally closes the laptop.
First three seconds: a desk lamp in a dark room, a clock at 23:40, and her laptop scrolling through an endless spreadsheet, with the line "Thesis due tomorrow. 1,498 answers."
What it adds: a person and the real app at work. The page shows charts and numbers, but never the app itself or the moment it saves someone.

## 2. "Same file, two afternoons" (a before and after)

A split screen with the same survey file twice. On the left, someone checks it by hand: sorting columns, scrolling, highlighting rows, a clock running. On the right, the same file goes into the real SurveyGuard app and is done in 8.4 seconds, with ten respondents flagged and a reason next to each. Then the left side gives up.
First three seconds: two identical spreadsheets side by side, both timers at 0:00, both starting at once.
What it adds: the work SurveyGuard replaces, made visible. The page says "8.4 s" but never shows what the alternative feels like. The hand-checking time is illustrative and labelled that way.

## 3. "During fieldwork" (the app at its best, a concept)

A survey wave in progress: answers arrive from phones, and a live board flags careless respondents as they come in, so the team can replace those interviews before the wave closes. The film opens on today's real detectors and moves to the future board, labelled "Concept: not built yet" on screen the whole time it is shown.
First three seconds: hands holding phones, and one thumb tapping the same answer down a whole grid.
What it adds: where SurveyGuard could get to. The page only describes what it does after the data is in.

---

Assumptions for all three: 28 to 32 s, 1920×1080, 30 fps, works fully without sound (no music source on this machine), English on-screen text. Real app screens come from the local Streamlit app driven by headless Chrome, using the synthetic sample `tests/fixtures/ess2_mock.csv` for anything that shows individual respondents, so no real respondent data appears.
