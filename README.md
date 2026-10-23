# SurveyGuard: Numeric Careless Responding Detector

## MVP usage

SurveyGuard is a deterministic Python CLI for flagging suspicious numeric survey response patterns. It calculates straightlining via intra-individual response variability (IRV), explicit contradiction rules, and Mahalanobis multivariate outliers, separately for each configured scale.

Install the Python dependencies in a Python 3.10+ environment:

```powershell
python -m pip install -r requirements.txt
```

Run the detector with a `.csv`, `.xlsx`, or `.sav` response file and a JSON rules file:

```powershell
python detect_anomalies.py data/wave1_raw.csv --rules config/scale_logic.json
```

Excel files are read directly through `openpyxl`. SPSS files are read with
raw numeric response codes (`convert_categoricals=False`), so value labels are
not passed to the numeric detectors.

Use `--output` to choose a result path. Without it, `wave1_raw.csv` becomes `wave1_scored.csv` beside the input:

```powershell
python detect_anomalies.py data/wave1_raw.csv `
	--rules config/scale_logic.json `
	--output output/wave1_scored.csv
```

Use `--report` to also write a Markdown diagnostic report. It includes the
processed and suspicious respondent counts, score statistics, detector counts
and percentages, and the flagged respondents with their reasons:

```powershell
python detect_anomalies.py data/wave1_raw.xlsx `
	--rules config/scale_logic.json `
	--output output/wave1_scored.csv `
	--report output/wave1_diagnostics.md
```

## Web interface

SurveyGuard also has a browser interface built with Streamlit. It uses the
same rules validation, loading, scoring, and report code as the CLI, so the
same files give the same results. The CLI is unchanged.

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

In the page that opens:

1. In the sidebar, upload the response file (`.csv`, `.xlsx`, or `.sav`) and
   the rules `.json` file.
2. Click **Run SurveyGuard**. A spinner shows while the data is processed and
   "Analysis complete!" appears when it is done.
3. Review the processed, suspicious, and average-score metrics, the detector
   results table with a bar chart of each detector's percentage, and the
   detector-flagged respondents table. Turn on **Show suspicious respondents
   only** to hide flagged respondents who are not suspicious.
4. Click **Download diagnostic report** to save `<input name>_diagnostics.md`,
   the same report the CLI writes with `--report`.
5. Click **Download cleaned data (CSV)** to save `<input name>_cleaned.csv`.

The cleaned file is always CSV, whatever the input format. It contains the
uploaded file's columns and rows in their original order, without the
suspicious respondents (quality score below the rules' `flag_threshold`,
50 by default) and without any scoring columns. Respondents that could not be
scored are kept. The file is written by pandas, so values can be formatted
differently from the original file: SPSS codes appear as raw numbers
(e.g. `3.0`), and integer columns with missing values become decimals. Running
SurveyGuard again on the cleaned file can give different results, because the
Mahalanobis statistics are recalculated without the removed respondents.

Uploaded files are only stored in a temporary folder while the run is in
progress; the interface does not save a scored or cleaned CSV on disk.

## Rules configuration

Rules identify question columns by header name, not by physical CSV order. The
shipped `config/scale_logic.json` is an ESS-style configuration for the European
Social Survey institutional-trust and satisfaction items; you can try it on the
synthetic `tests/fixtures/ess_mock.csv`:

```powershell
python detect_anomalies.py tests/fixtures/ess_mock.csv `
	--rules config/scale_logic.json `
	--output output/ess_scored.csv `
	--report output/ess_diagnostics.md
```

```json
{
	"id_column": "idno",
	"scales": {
		"Trust_Institutions": {
			"columns": ["trstprl", "trstlgl", "trstplc", "trstplt", "trstprt"],
			"valid_min": 0,
			"valid_max": 10,
			"missing_codes": [77, 88, 99],
			"irv_threshold": 0,
			"mahalanobis_threshold": 11.070498
		},
		"Satisfaction": {
			"columns": ["stflife", "stfeco", "stfgov", "stfdem"],
			"valid_min": 0,
			"valid_max": 10,
			"missing_codes": [77, 88, 99],
			"irv_threshold": 0,
			"mahalanobis_threshold": 9.487729
		}
	},
	"contradictions": [
		{"conditions": [
			{"column": "trstplt", "op": ">", "value": 8},
			{"column": "trstprl", "op": "<", "value": 2}
		]}
	],
	"weights": {
		"straightlining": 1.0,
		"logical_contradiction": 1.0,
		"mahalanobis_outlier": 1.0
	},
	"flag_threshold": 50
}
```

The shipped file has two more contradiction rules (`trstprt>8 vs trstplt<2` and
`stfgov>8 vs stfdem<2`). They are heuristics and can be tuned freely.

- `scales` (required): one entry per scale. A scale name may only contain
  letters, digits, and underscores, and a column may belong to only one scale.
  - `columns`, `valid_min`, `valid_max`, and `mahalanobis_threshold` are required.
  - `missing_codes` defaults to `[]`; the codes must lie outside the valid range.
  - `irv_threshold` defaults to `0`.
- `contradictions` (default `[]`): each rule is an AND of at least two
  conditions. A condition compares one scale column with a number using `>`,
  `>=`, `<`, `<=`, or `==`. A rule is skipped for a respondent when any of its
  columns is missing or invalid. With no rules, the contradiction detector is
  unavailable and does not affect the score.
- `weights` default to `1.0` per detector, `flag_threshold` defaults to `50`,
  and `id_column` is optional.

Detectors run per scale. Straightlining checks each complete scale. Mahalanobis
uses each scale's own columns, valid respondents, covariance matrix, and
threshold. The ESS thresholds are the chi-square 0.95 quantiles for 5 and 4
items. The scored CSV has one `mahalanobis_distance_<scale>` column per scale.
`flag_reasons` uses these labels, separated by `;`:

| Reason | Meaning |
| --- | --- |
| `Straightlining_<scale>` | IRV of the scale is at or below its `irv_threshold` |
| `Contradiction: trstplt>8 vs trstprl<2` | every condition of that rule holds |
| `Mahalanobis_<scale>` | squared distance on the scale is above its threshold |

Each detector adds a penalty of 1 when it triggers on at least one scale or rule,
so two straightlining scales cost the same as one.

### Migrating from the old rules format

Rules files with `blocks`, `inverted_pairs`, or `thresholds` are rejected with an
error. To convert one:

- Rename `blocks` to `scales`, `min`/`max` to `valid_min`/`valid_max`, and
  `missing_values` to `missing_codes`.
- Move `thresholds.mahalanobis_outlier` into each scale as `mahalanobis_threshold`.
- Replace each inverted pair with two rules: a high-high rule (both items
  `>= high_min`) and a low-low rule (both items `<= low_max`).

Reason labels changed from `Straightlining_Error:<block>`, `Mahalanobis_Outlier`,
and `Logical_Contradiction:<a>/<b>` to the labels above. For automated
processing, prefer the stable `*_triggered` columns.

### Spike calibration

The spike calibration rules live in `config/spike_logic.json`. They define one
`Extraversion` scale over `EXT1`-`EXT4` (1-5), and the former `EXT2`/`EXT3`
inverted pair as two rules with zero weight:

```powershell
python detect_anomalies.py spike_data.csv --rules config/spike_logic.json
```

The initial 10-item spike run flagged 0.2% of clean respondents for straightlining,
25.4% for logical contradictions, and 71.9% for Mahalanobis at $D^2=6$. Because
the configured scale has four items, `run_spike.py` now evaluates `EXT1` through
`EXT4` together. On those four items, the rates are 2.1% for straightlining,
25.4% for logical contradictions, and 15.7% for Mahalanobis at the legacy $D^2=6$
threshold. The recalibrated $D^2$ threshold is `9.829530`, which flags 50 of
1,000 respondents (5%) on the four-item spike data. Logical contradictions remain
visible in `flag_reasons` but have zero score weight pending validation against
labeled clean responses.

The quality score is calculated as:

`100 * (1 - weighted_average_detector_penalty)`

where `100` is good quality and lower scores are more suspicious. A score below `flag_threshold` receives `suspicious: true`. The scored CSV preserves all original columns and appends `quality_score`, `suspicious`, `flag_reasons`, detector trigger and availability fields, and `data_quality` markers. If none of a respondent's positive-weight detectors can be evaluated, the score and suspicious status are blank.

Configuration and missing question columns fail fast. Each scale may define numeric `missing_codes`, such as `[77, 88, 99]` for the ESS refusal, don't-know, and no-answer codes. Configured missing codes are excluded from all detectors and receive a `Missing_Value` marker while the original raw value remains in the scored output; the respondent row is never dropped. Numeric values outside the scale's `valid_min`/`valid_max` range are excluded from all detectors and receive an `Invalid_Value` marker. Other missing or non-numeric values in an individual row receive `Missing_Value` or `Invalid_Value` markers; values are not imputed. Unavailable detector results are excluded from the weighted score. Singular Mahalanobis covariance produces a controlled error. The console summary and optional Markdown report distinguish detector-triggered respondents from respondents below the suspicious threshold, report missing and invalid rows separately, explain that not-scored rows had no positive-weight detector with enough valid responses, and label the reasons table as detector-triggered rather than automatically suspicious.

The repository uses synthetic or public anonymized data only. It does not perform NLP, unsupervised machine learning, GUI work, or automatic respondent deletion.

Run tests with:

```powershell
python -m pytest -q
```

## 1. The demo
I open a terminal and run `python detect_anomalies.py data/wave1_raw.csv --rules config/scale_logic.json`. It processes 2,500 respondents and prints a summary to the console: "Flagged 142 suspicious records. Main drivers: Straightlining (80), Logical Contradiction (42), Multivariate Outlier (20)". I open the generated `output/wave1_scored.csv`, where every respondent has a new `quality_score` column (0-100) and a `flag_reasons` column detailing why they failed. I sort by the score and immediately see the worst offenders ready to be excluded.

## 2. The shape
in     a CSV of numeric survey responses and a JSON metadata file defining Likert grids and inverted item pairs.
out    a scored CSV with appended quality metrics, and a short summary printed to the console.
in between   calculates Intra-individual Response Variability (IRV) for straightlining, Mahalanobis distance for multivariate outliers, and cross-checks reversed items for logical consistency based on the JSON rules.

## 3. The size
**What the first useful version does:**
* Calculates IRV to detect straightlining (zero variance) across specific question blocks defined in the JSON.
* Calculates Mahalanobis distance ($D^2$) to identify multivariate outliers (respondents with highly unusual answering patterns compared to the sample centroid).
* Checks deterministic logical contradictions (e.g., scoring 5 on both Q2 and its exact opposite, Q5).
* Outputs a clean, reproducible CSV with the appended scores.

**What it explicitly does NOT do this term:**
* Any form of Natural Language Processing (NLP) or text analysis for open-ended questions.
* Unsupervised Machine Learning (e.g., Isolation Forests). The scoring remains strictly deterministic and based on classical survey statistics.
* A graphical user interface (GUI) or browser dashboard.
* Automated deletion of respondents (it only flags them).

## 4. How we would know it works
* Given a mock respondent row containing the exact same value (e.g., '3') across a 10-item Likert grid, it flags the row with `Straightlining_Error` and an IRV of 0.
* Given a dataset with perfect multivariate normality, the calculated centroid's Mahalanobis distance to itself returns exactly 0.
* Given a dataset with perfectly collinear variables, the Mahalanobis calculation catches the singular matrix error and halts with a clear error message instead of crashing natively.

## 5. What could stop this
* **The Math (Singular Matrices):** Survey items are often highly correlated. Calculating Mahalanobis distance requires inverting a covariance matrix. If items are perfectly collinear, the matrix becomes singular. I will need to implement pseudo-inverses or a dimensionality reduction step (PCA) to prevent mathematical crashes.
* **Missing Values (NAs):** Standard distance metrics fail when a respondent skipped a question. I must define a strict strategy (e.g., listwise deletion for the calculation, or mean imputation) before calculating the distances.
* **Data Privacy:** Real survey data with bots and careless responders is often proprietary or contains PII. I will use an open-access dataset (e.g., the Big Five Personality Test dataset from OpenPsychometrics) to build and test the tool, safely pushing it to GitHub.

## 6. Teacher's feedback
* ** What works: your tests are mathematical identities rather than impressions — the centroid's distance to itself is exactly 0, a perfectly collinear matrix produces a clear error instead of a native crash. That is unusually rigorous for week two, and choosing an open dataset means it all runs in a public repository.

* ** For the specification: IRV, Mahalanobis and reversed-item checks are textbook formulas — an hour of work, tests included. The project is the next question: where is the threshold, and what does it cost you in each direction? Flag too aggressively and you drop real respondents, possibly not at random. And the question a survey methodologist actually asks is not who is careless, but whether cleaning changes the substantive answer at all.
