# SurveyGuard: Numeric Careless Responding Detector

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
