# survey-quality-detection Specification

## Purpose

SurveyGuard provides a reproducible, auditable way to identify suspicious numeric survey response patterns without deleting respondents or relying on opaque machine learning.

## Requirements

### Requirement: Validate configured survey inputs
The system SHALL read a response file with a `.csv`, `.xlsx`, or `.sav` extension and a JSON rules file, identify survey questions by header name, and fail fast with a clear error when the rules are invalid, a configured question column is missing, or the input extension is unsupported. When reading an SPSS file, the system SHALL expose raw numeric response codes rather than value-label text.

#### Scenario: Valid input and rules
- **WHEN** a `.csv`, `.xlsx`, or `.sav` response file contains all configured question columns and the JSON contains valid blocks, ranges, pairs, weights, and thresholds
- **THEN** processing starts and the configured question columns are used regardless of their physical input order

#### Scenario: Raw numeric SPSS values
- **WHEN** a valid `.sav` file contains numeric codes with SPSS value labels
- **THEN** the loaded question values are the numeric codes and not the value-label strings

#### Scenario: Missing configured question column
- **WHEN** a question named in a configured block or inverted pair is absent from the input header
- **THEN** the command exits with a clear structural error and does not write a scored output

#### Scenario: Unsupported input extension
- **WHEN** the input file has an extension other than `.csv`, `.xlsx`, or `.sav`
- **THEN** the command exits with an explicit error naming the supported extensions and does not write a scored output

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
The system SHALL preserve every original input column and append auditable result fields including `quality_score`, `suspicious`, `flag_reasons`, detector results, and missing/invalid data markers.

#### Scenario: Scored CSV creation
- **WHEN** a valid `.csv`, `.xlsx`, or `.sav` run completes
- **THEN** the command writes the scored output as CSV to the explicit `--output` path or to an automatically derived `_scored.csv` path when no output path is provided

#### Scenario: Respondent metadata
- **WHEN** an optional `id_column` or other non-question metadata columns are present
- **THEN** those columns remain unchanged and are excluded from all statistical calculations

### Requirement: Report processing summary
The system SHALL print processed count, suspicious count, per-detector counts, missing/invalid counts, score statistics, and the output path after a successful run.

#### Scenario: Successful summary
- **WHEN** processing completes for a fixture containing flagged, clean, and invalid rows
- **THEN** the console summary reports each required aggregate and the exact scored-output location

### Requirement: Generate an optional diagnostic Markdown report
When the CLI receives `--report <path.md>`, the system SHALL write a readable Markdown report for the same successful run. The report SHALL contain the processed respondent count, the `is_suspicious` respondent count, average and minimum `quality_score`, each of the straightlining, contradiction, and Mahalanobis detector trigger counts and percentages, and a table of flagged or most suspicious respondents with their concrete `reasons` values. Without `--report`, no report file is required.

#### Scenario: Diagnostic report is written
- **WHEN** a valid run completes with `--report diagnostics.md`
- **THEN** the command creates or replaces that path with Markdown containing all required aggregate metrics and a flagged-respondent table

#### Scenario: Detector percentages use processed respondents
- **WHEN** a detector triggers for a known number of respondents in a processed input
- **THEN** its report percentage equals its trigger count divided by the processed respondent count, expressed as a percentage

#### Scenario: Report includes concrete reasons
- **WHEN** one or more respondents are marked suspicious or have detector reasons
- **THEN** the report table includes their respondent identifier when available and the exact textual `reasons`/`flag_reasons` content

#### Scenario: Report failure is explicit
- **WHEN** the requested report path cannot be written
- **THEN** the command exits with a clear error rather than silently omitting or claiming success for the report

### Requirement: Deterministically verify extended input and reporting behavior
The project SHALL include deterministic unit and CLI tests covering `.xlsx` loading, raw-code `.sav` loading, unsupported extensions, report metrics, report reason content, and report-path failures.

#### Scenario: Test suite covers both features
- **WHEN** the focused unit and CLI tests are run
- **THEN** they verify the supported input behavior and the report's exact deterministic counts, percentages, and reason text

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

#### Scenario: Omitted optional settings
- **WHEN** a valid rules file omits inverted pairs, band boundaries, IRV threshold, and respondent identifier
- **THEN** the documented defaults are applied and processing can start without an id column

### Requirement: Define precise scoring defaults
The high band SHALL include values equal to `high_min`, and the low band SHALL include values equal to `low_max`. The quality score SHALL equal `100 * (1 - weighted_mean_penalty)`, where the weighted mean is the sum of each detector penalty multiplied by its weight divided by the sum of the included weights. Omitted detector weights SHALL default to `1.0`, and omitted `flag_threshold` SHALL default to `50`.

#### Scenario: Default scoring settings
- **WHEN** detector weights and the suspicious threshold are omitted and a response is evaluated at a band boundary
- **THEN** weights default to `1.0`, the threshold defaults to `50`, and boundary values are included in their configured high or low bands

### Requirement: Exclude unavailable detector results from scoring
The system SHALL exclude unavailable detector results from the respondent's weighted score and SHALL expose whether each detector result is available. If no positive-weight detector is available, `quality_score` and `suspicious` SHALL be unavailable and serialize as empty CSV values. The summary SHALL report the number of respondents not scored.

#### Scenario: Partially available detector results
- **WHEN** a respondent has an unavailable detector and another available detector
- **THEN** only available positive-weight detectors contribute to that respondent's quality score

#### Scenario: No available detector results
- **WHEN** every detector is unavailable for a respondent
- **THEN** the respondent remains in the output with empty `quality_score` and `suspicious` fields