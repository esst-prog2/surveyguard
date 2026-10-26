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

1. In the sidebar, upload the response file (`.csv`, `.xlsx`, or `.sav`). Under
   **Rules source**, either upload a rules `.json` file or choose one of the
   bundled rules files in `config/` (`config/ess1.json` to `config/ess11.json`,
   listed in natural order, then `config/scale_logic.json` and
   `config/spike_logic.json`). Uploaded
   rules files cannot use `include`, because their relative paths cannot be
   resolved; use a bundled file or the CLI for modular rules.
2. Click **Run SurveyGuard**. A spinner shows while the data is processed and
   "Analysis complete!" appears when it is done.
3. Review the processed, suspicious, and average-score metrics, the detector
   results table with a bar chart of each detector's percentage, and the
   detector-flagged respondents table, and the scale results table (the same
   table as in the report). Turn on **Show suspicious respondents only** to hide
   flagged respondents who are not suspicious.
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

## Modular ESS configuration and scale-aware scoring

A full ESS round has many scales in a fixed core and in rotating modules, so the
rules can be split into several files. `config/ess2.json` is the ESS round 2
configuration; it includes `config/ess/core.json`, `config/ess/r2_health.json`,
`config/ess/r2_econ_morality.json`, and `config/ess/r2_family_work.json`. Try it
on the synthetic `tests/fixtures/ess2_mock.csv`:

```powershell
python detect_anomalies.py tests/fixtures/ess2_mock.csv `
	--rules config/ess2.json `
	--output output/ess2_scored.csv `
	--report output/ess2_diagnostics.md
```

### Included files and rule-only variables

- `include` (default `[]`) lists rules files, relative to the file that lists
  them. Included files are merged depth-first, in list order, before the
  including file's own entries. An included file may only contain `include`,
  `scales`, `variables`, and `contradictions`; `weights`, `flag_threshold`,
  `mahalanobis_min_scales`, `id_column`, and `essround` belong in the root file. Circular
  includes, a file included twice, a scale or variable defined in two files, and
  a column used by two scales or variables are errors that name both files.
- `variables` (default `{}`) declares binary, categorical, count, and year
  columns that contradiction rules need but that are not scales, for example
  `"partner": {"valid_min": 1, "valid_max": 2, "missing_codes": [9]}`. Variables
  are never used by straightlining or Mahalanobis and never produce
  `Missing_Value` or `Invalid_Value` markers; a missing or invalid variable value
  only skips the rules that use it.

### Scale settings

| Setting | Default | Meaning |
| --- | --- | --- |
| `module` | none | `"core"` or `"rotating"`; only shown in the report |
| `required` | `true` | `false` skips the scale (and the rules on its columns) when none of its columns is in the data; a scale with only some columns present is an error |
| `detectors` | both | `["straightlining", "mahalanobis_outlier"]` or one of them |
| `min_items_straightlining` | none | straightlining does not run on scales with fewer items |
| `mahalanobis_threshold` or `mahalanobis_alpha` | required with Mahalanobis | give exactly one; alpha uses the chi-square `(1 - alpha)` quantile with the item count as degrees of freedom |
| `mahalanobis_min_rows_per_item` | `0` | Mahalanobis needs at least `max(2, ceil(value * items))` complete rows, otherwise it is not available on the scale |

Skipped scales are printed as `Skipped scales: ...` in the console summary and
listed, with the skipped rules, in the report.

### Minimum number of flagged Mahalanobis scales

With one Mahalanobis test per scale, "any scale flags the respondent" grows with
the number of scales: with 22 ESS scales at alpha 0.01, 555 of 1,498 real ESS
round 2 respondents (37%) are flagged on at least one scale. The root setting
`mahalanobis_min_scales` (m, default `1`, which is the former behaviour)
triggers the Mahalanobis detector only when a respondent is flagged on at least
m scales; `config/ess2.json` uses `3` (65 respondents, 4.3%). The penalty of
every detector stays `0` or `1`, so with three available detectors a respondent
flagged on three scales and nothing else scores `66.67`, and a respondent
flagged on two scales scores `100`. Below m, the scale-level flags still show in
the distance columns, in `detector_details` (`flagged_scales`), and in the
report's scale results, whose `Mahalanobis flags (scale-level)` column counts
every scale-level flag; the detector table counts only respondents who reached
m. A respondent with fewer than m scales that can be evaluated cannot get a
Mahalanobis flag; m is not lowered for them, because that would again penalise
respondents who completed fewer blocks.

### ESS round 2 choices

- Each of the 22 attitude scales uses `mahalanobis_alpha` 0.01,
  `min_items_straightlining` 5, and `mahalanobis_min_rows_per_item` 10. The
  missing codes were checked against the ESS round 2 SPSS metadata.
- Straightlining is switched off on four five-item scales where giving the same
  answer to every item is common in real data: Medicine_Approval,
  Wellbeing_Two_Weeks, Gender_Family_Attitudes, and Job_Choice_Importance.
- Behaviour and event-frequency blocks (media use, religious practice,
  experienced and own dishonesty, partner disagreement, medicine habits) are not
  scales, because their Mahalanobis outliers are real extremes rather than
  careless answers. Columns that rules need are declared as variables.
- The contradiction rules (opposite attitude pairs and household consistency)
  are conservative heuristics and can be tuned.
- Real ESS data has many `Missing_Value` markers, because filtered rotating
  blocks and "not applicable" codes such as 6 and 66 count as missing.

### ESS rounds 1 to 11

`config/ess1.json` to `config/ess11.json` cover every ESS round. Apart from
`config/ess2.json`, which keeps its own `config/ess/core.json`, each root file
includes `config/ess/common_core.json` (the scales and variables that every
round has with the same columns), `config/ess/rN_core.json` (the round's own
core scales, household variables, and rules), and the round's rotating modules
`config/ess/rN_<topic>.json`. The files were derived from the Hungarian SPSS
files of each round:

- Ranges and missing codes come from the value labels, because these files
  declare no SPSS user-missing values; codes labelled Refusal, Don't know, No
  answer, Not applicable, or Not available are missing codes.
- Every scale has at least three items with the same answer range; a core scale
  with fewer items in a round is left out of that round. Every scale uses
  `mahalanobis_alpha` 0.01, `min_items_straightlining` 5, and
  `mahalanobis_min_rows_per_item` 10, and straightlining is switched off where
  more than 5% of complete real answers are straightlined.
- The contradiction rules follow ESS round 2 and use only variables the round
  has. The age rules use the fieldwork year Y of the round: `agea <= 30` with
  `yrbrn <= Y-36`, and `agea >= 60` with `yrbrn >= Y-54`.

Each ESS root file sets `essround`. A rules file with `essround` only accepts
data whose `essround` column has that value in every non-empty cell; data from
another round, data without an `essround` column, and an empty `essround` column
stop with a structural error such as
`Rules file expects ESS round 3, but the data contains essround 4`, on the
command line and in the web interface. Rules files without `essround` do not
check the round. `essround` must be a positive integer and may only be set in
the root file.

The real ESS files stay out of the repository: `.gitignore` ignores
`ess_sav_files/` and every `*.sav` file. Keep the files there to run a round,
for example:

```powershell
python detect_anomalies.py ess_sav_files/ESS7_HU_weighted_raw.sav `
	--rules config/ess7.json `
	--output output/ess7_scored.csv `
	--report output/ess7_diagnostics.md
```

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
