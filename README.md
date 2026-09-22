# SurveyGuard: Numeric Careless Responding Detector

## MVP usage

SurveyGuard is a deterministic Python CLI for flagging suspicious numeric survey response patterns. It calculates straightlining via intra-individual response variability (IRV), inverted-item contradictions, and Mahalanobis multivariate outliers.

Install the Python dependencies in a Python 3.10+ environment:

```powershell
python -m pip install -r requirements.txt
```

Run the detector with a CSV and JSON rules file:

```powershell
python detect_anomalies.py data/wave1_raw.csv --rules config/scale_logic.json
```

Use `--output` to choose a result path. Without it, `wave1_raw.csv` becomes `wave1_scored.csv` beside the input:

```powershell
python detect_anomalies.py data/wave1_raw.csv `
	--rules config/scale_logic.json `
	--output output/wave1_scored.csv
```

## Rules configuration

Rules identify question columns by header name, not by physical CSV order. Each block defines its columns and Likert range. `high_min` and `low_max` define the high-high and low-low contradiction bands for inverted pairs.

```json
{
	"id_column": "respondent_id",
	"blocks": {
		"attitude_scale": {
			"columns": ["Q1", "Q2", "Q3", "Q4"],
			"min": 1,
			"max": 5,
			"high_min": 4,
			"low_max": 2,
			"irv_threshold": 0
		}
	},
	"inverted_pairs": [["Q2", "Q3", "attitude_scale"]],
	"weights": {
		"straightlining": 1.0,
		"logical_contradiction": 1.0,
		"mahalanobis_outlier": 1.0
	},
	"thresholds": {"mahalanobis_outlier": 6},
	"flag_threshold": 50
}
```

The quality score is calculated as:

`100 * (1 - weighted_average_detector_penalty)`

where `100` is good quality and lower scores are more suspicious. A score below `flag_threshold` receives `suspicious: true`. The scored CSV preserves all original columns and appends `quality_score`, `suspicious`, `flag_reasons`, detector fields, and `data_quality` markers.

Configuration and missing question columns fail fast. Missing or non-numeric values in an individual row remain in the output and receive `Missing_Value` or `Invalid_Value` markers; values are not imputed. Singular Mahalanobis covariance produces a controlled error. The console summary reports processed and suspicious counts, detector counts, data-quality counts, score statistics, and the output path.

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
