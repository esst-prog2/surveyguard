# SurveyGuard promo page: content draft (step 2, office-hours)

Status: draft, waiting for approval. No code yet.

## Hero

**Headline:** Find the careless respondents before they find their way into your results.

**Subline:** SurveyGuard scans numeric survey data for straightlining, contradictory answers, and multivariate outliers, then hands you a cleaned file and a report that explains every flag.

**Primary action:** Try it in 3 commands
**Secondary action:** View on GitHub

## What it is for

Every survey has respondents who click through without reading: the same answer down a whole grid, "I fully trust politicians" next to "I don't trust parliament at all", or a pattern no one else in the sample produces. Left in, they quietly bend means, correlations, and scale reliabilities.

SurveyGuard checks each respondent with three transparent detectors:

- **Straightlining:** zero response variability (IRV) inside a scale.
- **Logical contradictions:** rules you write in plain JSON, for example `trstplt > 8` and `trstprl < 2`.
- **Mahalanobis outliers:** answer patterns far from the rest of the sample, scale by scale.

The three results are combined into a 0 to 100 quality score. Below the threshold (50 by default), a respondent is marked suspicious, and the report says exactly which rule or scale caused it. No black box, no machine learning, same input, same output.

## Who it is for

- **Social science students and researchers** working with the European Social Survey or similar questionnaires, who need a defensible data-cleaning step for a thesis or paper.
- **Survey methodologists and data managers** who want to screen a new wave before anyone starts the analysis.
- **Teachers** who want to show what careless responding looks like in real data, not in a textbook example.

You do not need to write code: the browser interface does everything. If you prefer scripts, the same engine runs from the command line.

## Proof (numbers strip)

- **1,498** Hungarian ESS round 2 respondents checked
- **10** flagged as suspicious (0.67%)
- **8.4 seconds** from upload to result, down from 397 seconds before the vectorised rewrite
- **ESS rounds 1 to 11** ready-made rules files included

## See it, don't just trust it

- **Straightlining heatmap:** click a flagged respondent and see their answers cell by cell; a single-colour row is a straightliner.
- **Mahalanobis PCA map:** every respondent as a point on the first two principal components; outliers in red, flagged respondents as outlined diamonds.
- **Score distribution:** a histogram of quality scores with the threshold line, on a log scale so the few suspicious cases stay visible.
- **Respondent drill-down:** the triggered contradiction rules written out next to the person's actual answers.

## How to try it

1. Install: `python -m pip install -r requirements.txt`
2. Start: `python -m streamlit run app.py`
3. In the browser, upload a `.csv`, `.xlsx`, or `.sav` file, choose a bundled rules file (for example `config/ess2.json`), and click **Run SurveyGuard**.

You get a cleaned CSV without the suspicious respondents and a Markdown diagnostic report you can attach to your methods section.

Command-line alternative:
`python detect_anomalies.py data.sav --rules config/ess2.json --report report.md`

## Footer

SurveyGuard, a Python project built for the Advanced Programming course. Open source on GitHub (esst-prog2/surveyguard). Your data stays on your machine: uploads live in a temporary folder only while the run is in progress.
