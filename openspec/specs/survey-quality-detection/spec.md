# survey-quality-detection Specification

## Purpose

SurveyGuard provides a reproducible, auditable way to identify suspicious numeric survey response patterns without deleting respondents or relying on opaque machine learning.

## Requirements

### Requirement: Validate configured survey inputs
The system SHALL read a CSV response file and a JSON rules file, identify survey questions by CSV header name, and fail fast with a clear error when the rules are invalid or a configured question column is missing.

#### Scenario: Valid input and rules
- **WHEN** the CSV contains all configured question columns and the JSON contains valid blocks, ranges, pairs, weights, and thresholds
- **THEN** processing starts and the configured question columns are used regardless of their physical CSV order

#### Scenario: Missing configured question column
- **WHEN** a question named in a configured block or inverted pair is absent from the CSV header
- **THEN** the command exits with a clear structural error and does not write a scored output

### Requirement: Detect straightlining
The system SHALL calculate population variance (IRV, divisor `n`) for each complete configured question block and SHALL identify a straightlining response when that variance is less than or equal to the block's `irv_threshold`.

#### Scenario: Constant Likert block
- **WHEN** a respondent answers every item in a configured ten-item block with `3`
- **THEN** the block IRV is `0` and the respondent receives a `Straightlining_Error` reason

#### Scenario: Non-constant Likert block
- **WHEN** a respondent has non-zero variability in a configured block
- **THEN** the system SHALL not mark that block as straightlining solely because the block was evaluated

### Requirement: Detect multivariate outliers
The rules SHALL provide a numeric `thresholds.mahalanobis_outlier`. The system SHALL calculate squared Mahalanobis distance using the sample covariance matrix (divisor `n-1`) for valid rows across configured numeric question columns and SHALL flag distances strictly greater than the configured threshold.

#### Scenario: Centroid row
- **WHEN** a valid respondent equals the sample centroid across the evaluated variables
- **THEN** the respondent's Mahalanobis distance is exactly `0`

#### Scenario: Singular covariance matrix
- **WHEN** the covariance matrix for the selected variables is singular
- **THEN** the system SHALL stop the affected run with a controlled mathematical error that explains the matrix problem, rather than exposing a native matrix exception

#### Scenario: Missing value in distance variables
- **WHEN** a respondent has a missing value in a variable required for Mahalanobis distance
- **THEN** the respondent remains in the scored CSV, receives a `Missing_Value` marker, and has no Mahalanobis score

### Requirement: Detect inverted-item contradictions
The system SHALL evaluate configured inverted item pairs using each block's configured scale and SHALL mark a contradiction when both values are in the configured high band or both are in the configured low band.

#### Scenario: High-high contradiction
- **WHEN** both items in an inverted pair are in the configured high band, such as `4` and `5` on a `1`-to-`5` scale
- **THEN** the respondent receives a logical-contradiction reason

#### Scenario: Low-low contradiction
- **WHEN** both items in an inverted pair are in the configured low band, such as `1` and `2` on a `1`-to-`5` scale
- **THEN** the respondent receives a logical-contradiction reason

#### Scenario: Middle response
- **WHEN** one or both pair values are in the middle band and neither high-high nor low-low rule applies
- **THEN** the pair does not trigger a contradiction solely from those values

### Requirement: Calculate auditable quality status
The system SHALL normalize each detector penalty to `0` through `1`, calculate a `quality_score` from `0` through `100` using the configured detector weights, and mark `suspicious` when the score is below the configured `flag_threshold`.

#### Scenario: Default scoring
- **WHEN** all detector weights are `1.0` and the configured `flag_threshold` is `50`
- **THEN** the weighted detector penalties produce a score where `100` means no penalty and a score below `50` means `suspicious`

#### Scenario: Detector reasons
- **WHEN** one or more detector rules trigger
- **THEN** the output contains the detector-specific reasons even when the aggregate score remains at or above the suspicious threshold

### Requirement: Preserve and annotate scored output
The system SHALL preserve every original CSV column and append auditable result fields including `quality_score`, `suspicious`, `flag_reasons`, detector results, and missing/invalid data markers.

#### Scenario: Scored CSV creation
- **WHEN** a valid run completes
- **THEN** the command writes the scored CSV to the explicit `--output` path or to an automatically derived `_scored.csv` path when no output path is provided

#### Scenario: Respondent metadata
- **WHEN** an optional `id_column` or other non-question metadata columns are present
- **THEN** those columns remain unchanged and are excluded from all statistical calculations

### Requirement: Report processing summary
The system SHALL print processed count, suspicious count, per-detector counts, missing/invalid counts, score statistics, and the output path after a successful run.

#### Scenario: Successful summary
- **WHEN** processing completes for a fixture containing flagged, clean, and invalid rows
- **THEN** the console summary reports each required aggregate and the exact scored-output location

### Requirement: Handle row-level data quality issues
The system SHALL continue processing when an individual respondent contains missing or non-numeric values, mark that row with a data-quality reason, and SHALL not silently impute values.

#### Scenario: Invalid respondent value
- **WHEN** one row contains a non-numeric response in a configured question column
- **THEN** the row is retained, receives an `Invalid_Value` marker, and calculations that require that value are marked unavailable

### Requirement: Protect repository data privacy
The repository SHALL use only synthetic or public anonymized data in demonstrations and tests and SHALL not require or commit real PII or proprietary survey data.

#### Scenario: Public fixture policy
- **WHEN** a developer adds a demonstration or test dataset
- **THEN** the dataset is synthetic or publicly anonymized and contains no real private respondent information

### Requirement: Define optional configuration defaults
When omitted, `inverted_pairs` SHALL default to an empty list, `high_min` SHALL default to `max - 1`, `low_max` SHALL default to `min + 1`, and `irv_threshold` SHALL default to `0`. The `id_column` setting SHALL be optional.

### Requirement: Define precise scoring defaults
The high band SHALL include values equal to `high_min`, and the low band SHALL include values equal to `low_max`. The quality score SHALL equal `100 * (1 - weighted_mean_penalty)`, where the weighted mean is the sum of each detector penalty multiplied by its weight divided by the sum of the included weights. Omitted detector weights SHALL default to `1.0`, and omitted `flag_threshold` SHALL default to `50`.

### Requirement: Exclude unavailable detector results from scoring
The system SHALL exclude unavailable detector results from the respondent's weighted score and SHALL expose whether each detector result is available. If no positive-weight detector is available, `quality_score` and `suspicious` SHALL be unavailable and serialize as empty CSV values. The summary SHALL report the number of respondents not scored.

#### Scenario: Partially available detector results
- **WHEN** a respondent has an unavailable detector and another available detector
- **THEN** only available positive-weight detectors contribute to that respondent's quality score

#### Scenario: No available detector results
- **WHEN** every detector is unavailable for a respondent
- **THEN** the respondent remains in the output with empty `quality_score` and `suspicious` fields