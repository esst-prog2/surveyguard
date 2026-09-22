## Context

The repository currently contains the MVP README and OpenSpec planning configuration but no implementation. The design therefore establishes a small, testable Python CLI architecture for the behavior in `specs/survey-quality-detection/spec.md`.

## Goals / Non-Goals

**Goals:**

- Keep detector calculations deterministic, independently testable, and explainable per respondent.
- Separate input validation, detector calculations, score aggregation, output writing, and CLI reporting.
- Make all thresholds, weights, question blocks, inverted pairs, and optional metadata configuration-driven.
- Preserve raw input data in the scored output and make every flag auditable.

**Non-Goals:**

- GUI, browser dashboard, service API, database, NLP, unsupervised machine learning, or automatic respondent deletion.
- Imputation of missing or invalid response values.
- Automatic selection of statistical thresholds from the data.

## Decisions

### Layered Python CLI

Use a thin `detect_anomalies.py` entry point over modules for configuration/schema validation, CSV loading, detector calculations, score aggregation, output serialization, and reporting. This keeps the CLI contract stable while allowing each mathematical detector to be unit tested directly. A monolithic script would be quicker initially but would make the required error and detector tests harder to isolate.

### Configuration model

Use a JSON rules document with an optional `id_column`, named question blocks, per-block `min`/`max` and high/low bands, inverted pairs, detector thresholds, detector weights, and `flag_threshold`. Question names are resolved against the CSV header; every unknown or missing reference is a structural error. Defaults are equal detector weights of `1.0` and `flag_threshold` `50`.

### Detector and score contract

Each detector returns a structured result containing its normalized penalty, whether it triggered, and a reason payload. The aggregator computes:

`quality_score = 100 * (1 - sum(weight_i * penalty_i) / sum(weight_i))`

with a clamped result in `0` through `100`. A missing detector value is excluded from the applicable calculation and surfaced as unavailable rather than imputed. The design favors explicit normalized penalties over combining raw IRV, distance, and boolean values with incomparable units.

### Mahalanobis failure policy

Use the covariance matrix and inverse required by the configured detector, but convert singular-matrix failures into a domain-specific controlled error. Do not silently substitute a pseudo-inverse or PCA in the MVP, because that would change the meaning of the configured detector without an explicit methodological decision.

### Output and reporting

Copy the input dataframe first, then append stable result columns for the aggregate score, status, reasons, detector results, and data-quality markers. The writer derives `<stem>_scored.csv` beside the input when `--output` is absent. The reporter prints stable labeled summary lines so the CLI integration test can assert behavior without depending on incidental formatting.

### Test strategy

Use `pytest` with synthetic fixtures. Unit tests cover each detector and the score aggregator; error tests cover missing configuration references, invalid row values, and singular covariance; an integration test invokes the CLI and verifies output columns, output naming, row preservation, and summary content. No fixture contains real PII or proprietary data.

## Risks / Trade-offs

- [Risk] Mahalanobis distance is sensitive to covariance quality and sample size -> Validate the selected numeric variables, surface singular matrices clearly, and document that the MVP uses the sample covariance without automatic robust estimation.
- [Risk] A fixed default threshold may flag too many or too few respondents for a new survey -> Keep all thresholds and weights in JSON and expose detector reasons so users can tune them without code changes.
- [Risk] Rows with missing values cannot receive a complete aggregate assessment -> Preserve the row and mark unavailable calculations explicitly instead of hiding or imputing the limitation.
- [Risk] CSV values may contain unexpected encodings or types -> Validate headers and numeric conversions before detector execution and emit actionable errors or row-level markers.