# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Social science students and researchers who work with European Social Survey (ESS) or similar numeric questionnaire data and need a defensible data-cleaning step before analysis, for a thesis or a paper. Secondary: survey methodologists and data managers screening a new wave. The promo page's first readers are the course teacher and classmates.

## Product Purpose
SurveyGuard flags careless survey respondents (straightlining, logical contradictions, multivariate outliers) and hands back a cleaned file and a diagnostic report that explains every flag. Success: a researcher can remove careless respondents with a step they can describe and defend in a methods section.

## Positioning
One flag is a warning, not a verdict. Three transparent detectors (IRV straightlining, JSON contradiction rules, Mahalanobis outliers per scale) combine into one 0 to 100 quality score; with the bundled ESS rule files and all three detectors available, one triggered detector scores 66.7 and stays in, two score 33.3 and are marked suspicious. Every flag names its rule or scale. Deterministic, no machine learning: same input, same output. Tools such as the R `careless` package compute indices for the user to combine; SurveyGuard combines them into a verdict, a cleaned file, and a report.

## Operating Context
Runs locally: a Streamlit web interface (`python -m streamlit run app.py`) and a CLI (`detect_anomalies.py`). Inputs: `.csv`, `.xlsx`, or `.sav` response files plus a JSON rules file; bundled rules for ESS rounds 1 to 11 in `config/`. Uploaded files stay in a temporary folder only during a run. It does not run online; the promo page links to the GitHub repository.

## Capabilities and Constraints
- Web interface: metrics, detector tables, straightlining heatmap, score histogram, Mahalanobis PCA map, respondent drill-down, report and cleaned CSV downloads.
- The promo page is static HTML/CSS with a little inline JS, in `docs/`, published by GitHub Pages from `main` / `docs`; everything in `docs/` becomes public.
- Page text is in English.

## Evidence on Hand
- Measured demo (README section 1): Hungarian ESS round 2 file, 1,498 respondents, 10 suspicious (0.67%), average score 96.22, 8.4 s from upload to result vs. 397 s before the October 2026 speed-up.
- Synthetic sample `tests/fixtures/ess2_mock.csv` with `config/ess2.json`: 284 respondents, 8 suspicious.
- Real chart screenshots from that synthetic sample: `docs/img/live-*.png`.
- No testimonials, users, logos, press, or benchmarks against other tools exist; none may be invented. The real ESS respondent files are not in the repository and must never be published.

## Product Principles
1. Show the real thing: real numbers, real charts, real commands that run as written.
2. Every claim must be checkable in the repository or a cited public source.
3. Explain, don't just flag: each result says why.
4. Nothing personal and no respondent data in anything published.
