# survey-quality-detection Specification

## Purpose

SurveyGuard provides a reproducible, auditable way to identify suspicious numeric survey response patterns without deleting respondents or relying on opaque machine learning.

## Requirements

### Requirement: Validate configured survey inputs
The system SHALL read a response file with a `.csv`, `.xlsx`, or `.sav` extension and a JSON rules file, identify survey questions by header name, and fail fast with a clear error when the rules are invalid, a configured question column is missing, or the input extension is unsupported. When reading an SPSS file, the system SHALL expose raw numeric response codes rather than value-label text, and when the configured `id_column` is numeric and every non-missing value is a whole number, the system SHALL load it as whole numbers so that identifiers such as `1026` are not shown as `1026.0`. The rules SHALL define a non-empty `scales` object. Each scale SHALL be identified by a name consisting only of letters, digits, and underscores, and SHALL define a non-empty `columns` list, numeric `valid_min` and `valid_max` with `valid_min` less than `valid_max`, and a positive numeric `mahalanobis_threshold`. Each scale MAY define numeric `missing_codes`; a missing code SHALL lie outside that scale's `valid_min`/`valid_max` range. A column SHALL belong to at most one scale. Configured missing codes SHALL remain in the preserved raw output, receive a `Missing_Value` marker, and be excluded from all detector calculations for that cell only; the respondent SHALL remain in the output. Numeric values outside a scale's `valid_min`/`valid_max` range that are not missing codes SHALL receive an `Invalid_Value` marker and be excluded from all detector calculations.

#### Scenario: Valid input and rules
- **WHEN** a `.csv`, `.xlsx`, or `.sav` response file contains all configured question columns and the JSON contains valid scales, ranges, contradiction rules, weights, and thresholds
- **THEN** processing starts and the configured question columns are used regardless of their physical input order

#### Scenario: Raw numeric SPSS values
- **WHEN** a valid `.sav` file contains numeric codes with SPSS value labels
- **THEN** the loaded question values are the numeric codes and not the value-label strings

#### Scenario: Whole-number SPSS identifiers
- **WHEN** a valid `.sav` file stores the configured `id_column` `idno` as numbers such as `1026`
- **THEN** the scored output, the diagnostic report, and the web interface show the identifier as `1026`, exactly as for the same data read from `.csv` or `.xlsx`

#### Scenario: Configured missing response codes
- **WHEN** a scale with `valid_min` `0` and `valid_max` `10` configures `77`, `88`, and `99` as `missing_codes` and a respondent answers `88` to one of its items
- **THEN** the raw `88` remains in the scored output, the respondent receives a `Missing_Value` marker, the respondent is not removed from the output, and that cell is treated as missing by every detector

#### Scenario: Out-of-range response value
- **WHEN** a numeric response is outside its scale's configured `valid_min`/`valid_max` range, such as `11` on a `0`-to-`10` scale, and is not a configured missing code
- **THEN** the raw value remains in the scored output, receives an `Invalid_Value` marker, and is excluded from every detector calculation

#### Scenario: Missing code inside the valid range
- **WHEN** a scale with `valid_min` `0` and `valid_max` `10` lists `5` in its `missing_codes`
- **THEN** rules loading fails with a clear configuration error naming the scale

#### Scenario: Column assigned to two scales
- **WHEN** the same column is listed in two different scales
- **THEN** rules loading fails with a clear configuration error naming the column

#### Scenario: Missing configured question column
- **WHEN** a question named in a configured scale is absent from the input header
- **THEN** the command exits with a clear structural error and does not write a scored output

#### Scenario: Unsupported input extension
- **WHEN** the input file has an extension other than `.csv`, `.xlsx`, or `.sav`
- **THEN** the command exits with an explicit error naming the supported extensions and does not write a scored output

### Requirement: Detect straightlining
The system SHALL calculate population variance (IRV, divisor `n`) separately for each configured scale whose items are all valid for the respondent, and SHALL identify straightlining on a scale when that variance is less than or equal to the scale's `irv_threshold`. Each straightlining scale SHALL add the reason `Straightlining_<scale name>`, using the configured scale name verbatim. A scale with any missing or invalid item SHALL be skipped for that respondent, and the straightlining detector SHALL be unavailable for a respondent only when every scale is skipped.

#### Scenario: Constant Likert block
- **WHEN** a respondent answers every item of the `Trust_Institutions` scale with `5`
- **THEN** that scale's IRV is `0` and the respondent receives the reason `Straightlining_Trust_Institutions`

#### Scenario: Only one scale is constant
- **WHEN** a respondent is constant on `Satisfaction` but varies on `Trust_Institutions`
- **THEN** the respondent receives `Straightlining_Satisfaction` and does not receive `Straightlining_Trust_Institutions`

#### Scenario: Non-constant Likert block
- **WHEN** a respondent has non-zero variability on every configured scale
- **THEN** the system SHALL not mark any scale as straightlining solely because it was evaluated

#### Scenario: Scale with a missing item
- **WHEN** one item of `Trust_Institutions` is a missing code and `Satisfaction` is complete
- **THEN** straightlining is evaluated on `Satisfaction` only and the detector remains available for that respondent

### Requirement: Detect multivariate outliers
Each scale SHALL provide a numeric `mahalanobis_threshold`. The system SHALL calculate squared Mahalanobis distance separately for each scale, using only that scale's columns, only the respondents whose items on that scale are all valid, and the sample covariance matrix of those respondents (divisor `n-1`). The system SHALL flag a respondent on a scale when the distance is strictly greater than that scale's threshold, and each flagged scale SHALL add the reason `Mahalanobis_<scale name>`. The scored output SHALL contain one `mahalanobis_distance_<scale name>` column per scale, empty where the distance was not calculated. The Mahalanobis detector SHALL be available for a respondent when a distance was calculated on at least one scale, and triggered when at least one scale flags the respondent.

#### Scenario: Centroid row
- **WHEN** a valid respondent equals the sample centroid of a scale's evaluated variables
- **THEN** the respondent's distance in that scale's distance column is exactly `0`

#### Scenario: Scale-specific outlier
- **WHEN** a respondent's distance exceeds the `Satisfaction` threshold but not the `Trust_Institutions` threshold
- **THEN** the respondent receives `Mahalanobis_Satisfaction`, does not receive `Mahalanobis_Trust_Institutions`, and the Mahalanobis detector is triggered

#### Scenario: Singular covariance matrix
- **WHEN** the covariance matrix of any scale's evaluated variables is singular
- **THEN** the system SHALL stop the affected run with a controlled mathematical error that names the scale and explains the matrix problem, rather than exposing a native matrix exception

#### Scenario: Missing value in distance variables
- **WHEN** a respondent has a missing value in one scale's items and complete values in another scale
- **THEN** the respondent remains in the scored CSV, receives a `Missing_Value` marker, has an empty distance for the incomplete scale, and has a distance for the complete scale

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
The system SHALL print processed count, suspicious count, detector-triggered count, per-detector counts, separate missing and invalid counts, not-scored count with its reason, score statistics, and the output path after a successful run.

#### Scenario: Successful summary
- **WHEN** processing completes for a fixture containing flagged, clean, and invalid rows
- **THEN** the console summary reports each required aggregate, distinguishes detector-triggered respondents from suspicious respondents, separates missing and invalid counts, explains not-scored rows, and reports the exact scored-output location

### Requirement: Generate an optional diagnostic Markdown report
When the CLI receives `--report <path.md>`, the system SHALL write a readable Markdown report for the same successful run. The report SHALL contain the processed respondent count, suspicious and detector-triggered respondent counts, separate missing and invalid counts, the not-scored count and its reason, average and minimum `quality_score`, each of the straightlining, contradiction, and Mahalanobis detector trigger counts and percentages, and a detector-triggered respondent table with concrete `reasons` values. Without `--report`, no report file is required.

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
When omitted, `contradictions` SHALL default to an empty list, a scale's `missing_codes` SHALL default to an empty list, and a scale's `irv_threshold` SHALL default to `0`. The `id_column` setting SHALL be optional. When `contradictions` is empty, the contradiction detector SHALL be unavailable for every respondent and SHALL not contribute to any score.

#### Scenario: Omitted optional settings
- **WHEN** a valid rules file omits contradictions, missing codes, IRV thresholds, and respondent identifier
- **THEN** the documented defaults are applied, processing can start without an id column, and no respondent receives a contradiction reason

### Requirement: Define precise scoring defaults
The quality score SHALL equal `100 * (1 - weighted_mean_penalty)`, where the weighted mean is the sum of each detector penalty multiplied by its weight divided by the sum of the included weights. Each of the three detectors (`straightlining`, `logical_contradiction`, `mahalanobis_outlier`) SHALL contribute a penalty of `1` when it is triggered on at least one scale or rule and `0` otherwise, regardless of how many scales or rules triggered. Omitted detector weights SHALL default to `1.0`, and omitted `flag_threshold` SHALL default to `50`.

#### Scenario: Default scoring settings
- **WHEN** detector weights and the suspicious threshold are omitted
- **THEN** weights default to `1.0` and the threshold defaults to `50`

#### Scenario: Several scales trigger the same detector
- **WHEN** a respondent straightlines on both `Trust_Institutions` and `Satisfaction` and no other detector triggers, with all three detectors available and weighted `1.0`
- **THEN** the respondent's `flag_reasons` contains both straightlining reasons and the `quality_score` is `66.67` when rounded to two decimals, the same as for a single straightlining scale

### Requirement: Exclude unavailable detector results from scoring
The system SHALL exclude unavailable detector results from the respondent's weighted score and SHALL expose whether each detector result is available. If no positive-weight detector is available, `quality_score` and `suspicious` SHALL be unavailable and serialize as empty CSV values. The summary SHALL report the number of respondents not scored.

#### Scenario: Partially available detector results
- **WHEN** a respondent has an unavailable detector and another available detector
- **THEN** only available positive-weight detectors contribute to that respondent's quality score

#### Scenario: No available detector results
- **WHEN** every detector is unavailable for a respondent
- **THEN** the respondent remains in the output with empty `quality_score` and `suspicious` fields

### Requirement: Detect explicit rule contradictions
The rules MAY define a `contradictions` list. Each rule SHALL contain a `conditions` list of at least two conditions; each condition SHALL name a `column` that belongs to a configured scale, an `op` that is one of `>`, `>=`, `<`, `<=`, or `==`, and a numeric `value`. A rule SHALL trigger for a respondent when every one of its conditions holds. A rule SHALL be evaluated only when all of its columns hold valid values for the respondent; otherwise it is skipped for that respondent. Each triggered rule SHALL add one reason of the form `Contradiction: <column><op><value> vs <column><op><value>`, with conditions joined by ` vs ` in their configured order and whole-number values written without a decimal part. The contradiction detector SHALL be available for a respondent when at least one rule was evaluated.

#### Scenario: Trust contradiction triggers
- **WHEN** a rule requires `trstplt` `>` `8` and `trstprl` `<` `2`, and a respondent answers `trstplt` `9` and `trstprl` `1`
- **THEN** the respondent receives exactly the reason `Contradiction: trstplt>8 vs trstprl<2`

#### Scenario: Boundary value does not trigger a strict condition
- **WHEN** the same rule is evaluated for a respondent with `trstplt` `8` and `trstprl` `1`
- **THEN** the rule does not trigger for that respondent

#### Scenario: Rule with a missing column value
- **WHEN** a respondent's `trstprl` is the missing code `77`
- **THEN** every rule that references `trstprl` is skipped for that respondent and does not produce a reason

#### Scenario: Invalid rule definition
- **WHEN** a rule has fewer than two conditions, uses an unsupported operator, has a non-numeric value, or references a column that is not in any scale
- **THEN** rules loading fails with a clear configuration error identifying the rule by its position in the list

### Requirement: Reject the legacy rules schema
The system SHALL reject a rules file that contains the legacy keys `blocks`, `inverted_pairs`, or `thresholds` with a clear configuration error that names the offending key and points to `scales` and `contradictions`. The legacy schema SHALL NOT be translated or partially applied.

#### Scenario: Legacy blocks file
- **WHEN** a rules file defines `blocks` and `inverted_pairs` instead of `scales`
- **THEN** rules loading fails with a configuration error naming the legacy key, and the command does not write a scored output

### Requirement: Provide an ESS reference configuration and fixture
The repository SHALL ship `config/scale_logic.json` as an ESS-style configuration with `id_column` `idno`, a `Trust_Institutions` scale of `trstprl`, `trstlgl`, `trstplc`, `trstplt`, and `trstprt`, and a `Satisfaction` scale of `stflife`, `stfeco`, `stfgov`, and `stfdem`, each with `valid_min` `0`, `valid_max` `10`, and `missing_codes` `77`, `88`, and `99`, and a `contradictions` list that includes the rule `trstplt` `>` `8` and `trstprl` `<` `2`. The repository SHALL also ship a synthetic ESS-like response file `tests/fixtures/ess_mock.csv` containing `idno`, all nine configured items, and at least one non-question metadata column, with rows that exercise straightlining on each scale, at least one contradiction, missing codes, an out-of-range value, a non-numeric value, and clean responses. The fixture SHALL contain no real respondent data.

#### Scenario: Reference configuration runs on the fixture
- **WHEN** the CLI is run on `tests/fixtures/ess_mock.csv` with `config/scale_logic.json`
- **THEN** the run succeeds and the scored output contains `Straightlining_Trust_Institutions`, `Straightlining_Satisfaction`, and `Contradiction: trstplt>8 vs trstprl<2` reasons on the rows designed to produce them

#### Scenario: Test suite uses the ESS configuration
- **WHEN** the full test suite is run after the change
- **THEN** every test passes, and the tests that exercise the end-to-end pipeline, CLI, report, and web interface use `config/scale_logic.json` with `tests/fixtures/ess_mock.csv` or files derived from them
