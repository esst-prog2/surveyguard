# survey-quality-detection Specification

## Purpose

SurveyGuard provides a reproducible, auditable way to identify suspicious numeric survey response patterns without deleting respondents or relying on opaque machine learning.

## Requirements

### Requirement: Validate configured survey inputs
The system SHALL read a response file with a `.csv`, `.xlsx`, or `.sav` extension and a JSON rules file together with every rules file it includes, identify survey questions by header name, and fail fast with a clear error when the rules are invalid, a column of a required scale or of a required variable is missing, some but not all columns of an optional scale are missing, or the input extension is unsupported. When reading an SPSS file, the system SHALL expose raw numeric response codes rather than value-label text, and when the configured `id_column` is numeric and every non-missing value is a whole number, the system SHALL load it as whole numbers so that identifiers such as `1026` are not shown as `1026.0`. The merged rules SHALL define a non-empty `scales` object. Each scale SHALL be identified by a name consisting only of letters, digits, and underscores, and SHALL define a non-empty `columns` list and numeric `valid_min` and `valid_max` with `valid_min` less than `valid_max`. Each scale whose detectors include `mahalanobis_outlier` SHALL define exactly one of a positive numeric `mahalanobis_threshold` or a numeric `mahalanobis_alpha` strictly between `0` and `1`; defining both, defining neither, or defining either one on a scale without the Mahalanobis detector SHALL be a configuration error. Each scale MAY define numeric `missing_codes`; a missing code SHALL lie outside that scale's `valid_min`/`valid_max` range. A column SHALL belong to at most one scale and SHALL NOT be both a scale column and a declared variable. Configured missing codes SHALL remain in the preserved raw output, receive a `Missing_Value` marker, and be excluded from all detector calculations for that cell only; the respondent SHALL remain in the output. Numeric values outside a scale's `valid_min`/`valid_max` range that are not missing codes SHALL receive an `Invalid_Value` marker and be excluded from all detector calculations.

#### Scenario: Valid input and rules
- **WHEN** a `.csv`, `.xlsx`, or `.sav` response file contains all columns of every required scale and the JSON contains valid scales, ranges, contradiction rules, weights, and thresholds
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

#### Scenario: Both a threshold and an alpha
- **WHEN** a scale defines both `mahalanobis_threshold` `11.070498` and `mahalanobis_alpha` `0.05`
- **THEN** rules loading fails with a clear configuration error naming the scale and stating that only one of the two may be given

#### Scenario: Threshold on a scale without the Mahalanobis detector
- **WHEN** a scale sets `detectors` to `["straightlining"]` and also defines `mahalanobis_alpha`
- **THEN** rules loading fails with a clear configuration error naming the scale

#### Scenario: Missing configured question column
- **WHEN** a question named in a required scale is absent from the input header
- **THEN** the command exits with a clear structural error and does not write a scored output

#### Scenario: Optional scale with only some columns present
- **WHEN** a scale with `required` `false` lists five columns and the input header contains three of them
- **THEN** the command exits with a clear structural error that names the scale and the two missing columns, and does not write a scored output

#### Scenario: Unsupported input extension
- **WHEN** the input file has an extension other than `.csv`, `.xlsx`, or `.sav`
- **THEN** the command exits with an explicit error naming the supported extensions and does not write a scored output

### Requirement: Detect straightlining
The system SHALL calculate population variance (IRV, divisor `n`) separately for each configured scale that is not skipped, whose `detectors` include `straightlining`, whose item count is at least its `min_items_straightlining` when that setting is given, and whose items are all valid for the respondent. The system SHALL identify straightlining on a scale when that variance is less than or equal to the scale's `irv_threshold`. Each straightlining scale SHALL add the reason `Straightlining_<scale name>`, using the configured scale name verbatim. A scale with any missing or invalid item SHALL be skipped for that respondent, a scale excluded by its `detectors` or by `min_items_straightlining` SHALL never be evaluated, and the straightlining detector SHALL be unavailable for a respondent only when no scale was evaluated for that respondent.

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

#### Scenario: Scale shorter than the straightlining minimum
- **WHEN** a three-item scale sets `min_items_straightlining` `5` and a respondent answers all three items with `4`
- **THEN** the respondent receives no straightlining reason for that scale, and when no other scale was evaluated for them the straightlining detector is unavailable

#### Scenario: Straightlining switched off for a scale
- **WHEN** a five-item scale sets `detectors` to `["mahalanobis_outlier"]` and a respondent answers all five items with `1`
- **THEN** the respondent receives no straightlining reason for that scale, while the Mahalanobis detector still evaluates the scale

### Requirement: Detect multivariate outliers
For each scale that is not skipped and whose `detectors` include `mahalanobis_outlier`, the system SHALL use the scale's configured `mahalanobis_threshold` or the threshold derived from its `mahalanobis_alpha`. The system SHALL calculate squared Mahalanobis distance separately for each such scale, using only that scale's columns, only the respondents whose items on that scale are all valid, and the sample covariance matrix of those respondents (divisor `n-1`). A scale SHALL be evaluated only when its number of valid respondents is at least the larger of `2` and the scale's item count multiplied by its `mahalanobis_min_rows_per_item`, rounded up; otherwise the Mahalanobis detector SHALL be not available on that scale for every respondent and no distance SHALL be calculated for it. The system SHALL flag a respondent on a scale when the distance is strictly greater than that scale's threshold. The rules MAY define a root-level `mahalanobis_min_scales`, a positive integer `m` that defaults to `1`. The Mahalanobis detector SHALL be triggered for a respondent only when the respondent is flagged on at least `m` scales; only then SHALL each flagged scale add the reason `Mahalanobis_<scale name>` to `flag_reasons`. When fewer than `m` scales flag the respondent, including when fewer than `m` scales have a distance for the respondent, the detector SHALL NOT be triggered and SHALL add no Mahalanobis reason, while the per-scale flags remain visible in `detector_details`, the distance columns, and the report's scale results. The scored output SHALL contain one `mahalanobis_distance_<scale name>` column per scale that is not skipped and has the Mahalanobis detector, empty where the distance was not calculated. The Mahalanobis detector SHALL be available for a respondent when a distance was calculated on at least one scale.

#### Scenario: Centroid row
- **WHEN** a valid respondent equals the sample centroid of a scale's evaluated variables
- **THEN** the respondent's distance in that scale's distance column is exactly `0`

#### Scenario: Scale-specific outlier
- **WHEN** a respondent's distance exceeds the `Satisfaction` threshold but not the `Trust_Institutions` threshold
- **THEN** the respondent receives `Mahalanobis_Satisfaction`, does not receive `Mahalanobis_Trust_Institutions`, and the Mahalanobis detector is triggered

#### Scenario: Singular covariance matrix
- **WHEN** the covariance matrix of any evaluated scale's variables is singular
- **THEN** the system SHALL stop the affected run with a controlled mathematical error that names the scale and explains the matrix problem, rather than exposing a native matrix exception

#### Scenario: Missing value in distance variables
- **WHEN** a respondent has a missing value in one scale's items and complete values in another scale
- **THEN** the respondent remains in the scored CSV, receives a `Missing_Value` marker, has an empty distance for the incomplete scale, and has a distance for the complete scale

#### Scenario: Too few valid rows on a scale
- **WHEN** a four-item scale sets `mahalanobis_min_rows_per_item` `10` and only 39 respondents have all four items valid
- **THEN** that scale's distance column is empty for every respondent, no respondent is flagged on that scale, and the scale does not count toward `mahalanobis_min_scales`

#### Scenario: Default minimum keeps the former behaviour
- **WHEN** a scale omits `mahalanobis_min_rows_per_item` and at least two respondents have all of its items valid
- **THEN** distances are calculated for that scale exactly as before the change

#### Scenario: Default minimum number of flagged scales
- **WHEN** the rules omit `mahalanobis_min_scales` and a respondent is flagged on exactly one of two scales
- **THEN** the Mahalanobis detector is triggered and the respondent receives that scale's `Mahalanobis_<scale name>` reason, exactly as before the change

#### Scenario: Fewer flagged scales than the minimum
- **WHEN** `mahalanobis_min_scales` is `3` and a respondent is flagged on two of three scales that have a distance for them
- **THEN** `mahalanobis_outlier_triggered` is false, `flag_reasons` contains no `Mahalanobis_` reason, and both scale-level flags appear in `detector_details` and are counted in the report's scale results

#### Scenario: Minimum number of flagged scales reached
- **WHEN** `mahalanobis_min_scales` is `3` and a respondent is flagged on three scales
- **THEN** `mahalanobis_outlier_triggered` is true and `flag_reasons` contains the three `Mahalanobis_<scale name>` reasons in configuration order

#### Scenario: Fewer evaluable scales than the minimum
- **WHEN** `mahalanobis_min_scales` is `3` and a respondent has a distance on only two scales, both above their thresholds
- **THEN** the Mahalanobis detector is available but not triggered for that respondent

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
The system SHALL print processed count, suspicious count, detector-triggered count, per-detector counts, separate missing and invalid counts, not-scored count with its reason, score statistics, and the output path after a successful run. When at least one optional scale was skipped because its columns are absent, the summary SHALL also print one line `Skipped scales: <names>` that lists the skipped scales by name, separated by `, `, in configuration order; when no scale was skipped, that line SHALL NOT be printed.

#### Scenario: Successful summary
- **WHEN** processing completes for a fixture containing flagged, clean, and invalid rows
- **THEN** the console summary reports each required aggregate, distinguishes detector-triggered respondents from suspicious respondents, separates missing and invalid counts, explains not-scored rows, and reports the exact scored-output location

#### Scenario: Skipped optional scales in the summary
- **WHEN** the rules contain two optional scales `Job_Demands` and `Study_Conditions` whose columns are all absent from the input
- **THEN** the summary contains the line `Skipped scales: Job_Demands, Study_Conditions`

#### Scenario: No skipped scales
- **WHEN** every configured scale is present in the input
- **THEN** the summary contains no `Skipped scales:` line and is otherwise worded exactly as before the change

### Requirement: Generate an optional diagnostic Markdown report
When the CLI receives `--report <path.md>`, the system SHALL write a readable Markdown report for the same successful run. The report SHALL contain the processed respondent count, suspicious and detector-triggered respondent counts, separate missing and invalid counts, the not-scored count and its reason, average and minimum `quality_score`, each of the straightlining, contradiction, and Mahalanobis detector trigger counts and percentages, and a detector-triggered respondent table with concrete `reasons` values. The report SHALL also contain a scale results table with one row per configured scale that is not skipped, in configuration order, showing the scale name, its module (or `-` when none is configured), its item count, its enabled detectors, its Mahalanobis threshold with six decimals and the threshold's source (`configured` or `alpha=<value>`), or `-` without the Mahalanobis detector, the number of respondents with all of its items valid, the number of respondents flagged for straightlining on it, the number of respondents whose distance on it exceeds its threshold (labelled as scale-level Mahalanobis flags, counted whether or not `mahalanobis_min_scales` was reached), and its Mahalanobis status (`available`, `not available (<valid> valid rows, needs <required>)`, or `-`). The detector table's Mahalanobis count SHALL be the number of respondents for whom the Mahalanobis detector was triggered, and the report SHALL state the configured `mahalanobis_min_scales` next to it so that it cannot be confused with the scale-level counts. The report SHALL list the skipped optional scales and the contradiction rules skipped because they reference absent columns, or state `None` for each. Without `--report`, no report file is required.

#### Scenario: Diagnostic report is written
- **WHEN** a valid run completes with `--report diagnostics.md`
- **THEN** the command creates or replaces that path with Markdown containing all required aggregate metrics, the scale results table, the skipped scales and rules, and a flagged-respondent table

#### Scenario: Detector percentages use processed respondents
- **WHEN** a detector triggers for a known number of respondents in a processed input
- **THEN** its report percentage equals its trigger count divided by the processed respondent count, expressed as a percentage

#### Scenario: Report includes concrete reasons
- **WHEN** one or more respondents are marked suspicious or have detector reasons
- **THEN** the report table includes their respondent identifier when available and the exact textual `reasons`/`flag_reasons` content

#### Scenario: Per-scale counts
- **WHEN** the CLI is run on `tests/fixtures/ess_mock.csv` with `config/scale_logic.json` and `--report`
- **THEN** the scale results table shows `Trust_Institutions` with 5 items, threshold `11.070498 (configured)`, 31 valid rows, 2 straightlining and 3 Mahalanobis flags, and `Satisfaction` with 4 items, threshold `9.487729 (configured)`, 31 valid rows, 3 straightlining and 2 Mahalanobis flags

#### Scenario: Scale-level and respondent-level Mahalanobis counts
- **WHEN** `mahalanobis_min_scales` is `3`, five respondents are flagged on exactly one scale each, and one respondent is flagged on three scales
- **THEN** the detector table shows `1` Mahalanobis respondent together with the minimum of `3` scales, and the scale results table counts all eight scale-level flags under its scale-level Mahalanobis column

#### Scenario: Derived threshold in the report
- **WHEN** a five-item scale sets `mahalanobis_alpha` `0.01`
- **THEN** its row in the scale results table shows the threshold `15.086272 (alpha=0.01)`

#### Scenario: Skipped scales and rules are listed
- **WHEN** an optional scale is skipped and a contradiction rule references one of its columns
- **THEN** the report names the skipped scale and the skipped rule's label, and that rule produces no reason for any respondent

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
When omitted, `include` SHALL default to an empty list, `variables` SHALL default to an empty object, `mahalanobis_min_scales` SHALL default to `1`, `contradictions` SHALL default to an empty list, a scale's `missing_codes` SHALL default to an empty list, a scale's `irv_threshold` SHALL default to `0`, a scale's `required` SHALL default to `true`, a scale's `detectors` SHALL default to `["straightlining", "mahalanobis_outlier"]`, a scale's `mahalanobis_min_rows_per_item` SHALL default to `0`, and a scale without `min_items_straightlining` SHALL have no straightlining item minimum. A scale's `module` SHALL be optional and SHALL only be shown in the report. The `id_column` setting SHALL be optional. When `contradictions` is empty, the contradiction detector SHALL be unavailable for every respondent and SHALL not contribute to any score.

#### Scenario: Omitted optional settings
- **WHEN** a valid rules file omits include, variables, the minimum number of Mahalanobis scales, contradictions, missing codes, IRV thresholds, required, detectors, item and row minimums, module, and respondent identifier
- **THEN** the documented defaults are applied, processing can start without an id column, every scale runs both detectors exactly as before the change, and no respondent receives a contradiction reason

### Requirement: Define precise scoring defaults
The quality score SHALL equal `100 * (1 - weighted_mean_penalty)`, where the weighted mean is the sum of each available detector's penalty multiplied by its weight divided by the sum of the included weights. Each of the three detectors (`straightlining`, `logical_contradiction`, `mahalanobis_outlier`) SHALL contribute a penalty of `1` when it is triggered and `0` otherwise, regardless of how many scales or rules triggered: straightlining is triggered when at least one evaluated scale straightlines, the contradiction detector when at least one rule triggers, and the Mahalanobis detector when the respondent is flagged on at least `mahalanobis_min_scales` scales. Omitted detector weights SHALL default to `1.0`, and omitted `flag_threshold` SHALL default to `50`.

#### Scenario: Default scoring settings
- **WHEN** detector weights and the suspicious threshold are omitted
- **THEN** weights default to `1.0` and the threshold defaults to `50`

#### Scenario: Several scales trigger the same detector
- **WHEN** a respondent straightlines on both `Trust_Institutions` and `Satisfaction` and no other detector triggers, with all three detectors available and weighted `1.0`
- **THEN** the respondent's `flag_reasons` contains both straightlining reasons and the `quality_score` is `66.67` when rounded to two decimals, the same as for a single straightlining scale

#### Scenario: Mahalanobis flags below the minimum do not cost points
- **WHEN** `mahalanobis_min_scales` is `3`, a respondent is flagged on two scales, and no other detector triggers, with all three detectors available and weighted `1.0`
- **THEN** the `quality_score` is `100.00`

#### Scenario: Mahalanobis minimum reached
- **WHEN** `mahalanobis_min_scales` is `3`, a respondent is flagged on three scales, and no other detector triggers, with all three detectors available and weighted `1.0`
- **THEN** the `quality_score` is `66.67` when rounded to two decimals

#### Scenario: Single-scale rules keep their results
- **WHEN** the rules define exactly one scale and omit `mahalanobis_min_scales`, as in `config/spike_logic.json`
- **THEN** every respondent's `quality_score`, `suspicious`, `flag_reasons`, and `*_triggered` values equal those produced before the change

### Requirement: Exclude unavailable detector results from scoring
The system SHALL exclude unavailable detector results from the respondent's weighted score and SHALL expose whether each detector result is available. If no positive-weight detector is available, `quality_score` and `suspicious` SHALL be unavailable and serialize as empty CSV values. The summary SHALL report the number of respondents not scored.

#### Scenario: Partially available detector results
- **WHEN** a respondent has an unavailable detector and another available detector
- **THEN** only available positive-weight detectors contribute to that respondent's quality score

#### Scenario: No available detector results
- **WHEN** every detector is unavailable for a respondent
- **THEN** the respondent remains in the output with empty `quality_score` and `suspicious` fields

### Requirement: Detect explicit rule contradictions
The rules MAY define a `contradictions` list. Each rule SHALL contain a `conditions` list of at least two conditions; each condition SHALL name a `column` that belongs to a configured scale or is a declared variable, an `op` that is one of `>`, `>=`, `<`, `<=`, or `==`, and a numeric `value`. A rule SHALL trigger for a respondent when every one of its conditions holds. A rule SHALL be evaluated only when all of its columns hold valid values for the respondent; otherwise it is skipped for that respondent. A rule that references a column of a skipped optional scale or an absent optional variable SHALL be skipped for every respondent and reported as a skipped rule. Each triggered rule SHALL add one reason of the form `Contradiction: <column><op><value> vs <column><op><value>`, with conditions joined by ` vs ` in their configured order and whole-number values written without a decimal part. The contradiction detector SHALL be available for a respondent when at least one rule was evaluated.

#### Scenario: Trust contradiction triggers
- **WHEN** a rule requires `trstplt` `>` `8` and `trstprl` `<` `2`, and a respondent answers `trstplt` `9` and `trstprl` `1`
- **THEN** the respondent receives exactly the reason `Contradiction: trstplt>8 vs trstprl<2`

#### Scenario: Boundary value does not trigger a strict condition
- **WHEN** the same rule is evaluated for a respondent with `trstplt` `8` and `trstprl` `1`
- **THEN** the rule does not trigger for that respondent

#### Scenario: Rule with a missing column value
- **WHEN** a respondent's `trstprl` is the missing code `77`
- **THEN** every rule that references `trstprl` is skipped for that respondent and does not produce a reason

#### Scenario: Rule on a rule-only variable
- **WHEN** `partner` is a declared variable with `valid_min` `1` and `valid_max` `2`, a rule requires `partner` `==` `2` and `dsgrhwk` `>=` `1`, and a respondent answers `partner` `2` and `dsgrhwk` `3`
- **THEN** the respondent receives exactly the reason `Contradiction: partner==2 vs dsgrhwk>=1`

#### Scenario: Invalid rule definition
- **WHEN** a rule has fewer than two conditions, uses an unsupported operator, has a non-numeric value, or references a column that is neither in any scale nor a declared variable
- **THEN** rules loading fails with a clear configuration error identifying the rule by its position in the list and the rules file that defines it

### Requirement: Reject the legacy rules schema
The system SHALL reject a rules file, including any included rules file, that contains the legacy keys `blocks`, `inverted_pairs`, or `thresholds` with a clear configuration error that names the offending key and the file and points to `scales` and `contradictions`. The legacy schema SHALL NOT be translated or partially applied.

#### Scenario: Legacy blocks file
- **WHEN** a rules file defines `blocks` and `inverted_pairs` instead of `scales`
- **THEN** rules loading fails with a configuration error naming the legacy key, and the command does not write a scored output

#### Scenario: Legacy key in an included file
- **WHEN** a root rules file includes a file that defines `thresholds`
- **THEN** rules loading fails with a configuration error naming `thresholds` and the included file

### Requirement: Provide an ESS reference configuration and fixture
The repository SHALL ship `config/scale_logic.json` as an ESS-style configuration with `id_column` `idno`, a `Trust_Institutions` scale of `trstprl`, `trstlgl`, `trstplc`, `trstplt`, and `trstprt`, and a `Satisfaction` scale of `stflife`, `stfeco`, `stfgov`, and `stfdem`, each with `valid_min` `0`, `valid_max` `10`, and `missing_codes` `77`, `88`, and `99`, and a `contradictions` list that includes the rule `trstplt` `>` `8` and `trstprl` `<` `2`. The repository SHALL also ship a synthetic ESS-like response file `tests/fixtures/ess_mock.csv` containing `idno`, all nine configured items, and at least one non-question metadata column, with rows that exercise straightlining on each scale, at least one contradiction, missing codes, an out-of-range value, a non-numeric value, and clean responses. The fixture SHALL contain no real respondent data.

#### Scenario: Reference configuration runs on the fixture
- **WHEN** the CLI is run on `tests/fixtures/ess_mock.csv` with `config/scale_logic.json`
- **THEN** the run succeeds and the scored output contains `Straightlining_Trust_Institutions`, `Straightlining_Satisfaction`, and `Contradiction: trstplt>8 vs trstprl<2` reasons on the rows designed to produce them

#### Scenario: Test suite uses the ESS configuration
- **WHEN** the full test suite is run after the change
- **THEN** every test passes, and the tests that exercise the end-to-end pipeline, CLI, report, and web interface use `config/scale_logic.json` with `tests/fixtures/ess_mock.csv` or files derived from them

### Requirement: Compose rules from included files
A rules file MAY define an `include` list of rules-file paths, each resolved relative to the directory of the file that lists it. The system SHALL load included files depth-first, in list order, before the including file's own entries, and SHALL merge their `scales`, `variables`, and `contradictions` in that order. An included file SHALL contain only `include`, `scales`, `variables`, and `contradictions`; `weights`, `flag_threshold`, `mahalanobis_min_scales`, and `id_column` SHALL be accepted only in the root file. All validation rules SHALL apply to the merged configuration. The system SHALL reject, with a clear configuration error, an include cycle (naming the files of the cycle in order), a file that is included more than once, an included file that cannot be read, a scale name or variable defined in two files, and a column that belongs to scales or variables of two files; each error about a conflict SHALL name both files.

#### Scenario: Include chain
- **WHEN** `root.json` includes `modules/a.json`, which includes `b.json` in the same `modules` folder, and each file defines one scale
- **THEN** the merged rules contain the scales of `b.json`, `modules/a.json`, and `root.json` in that order, and the run produces the same result as a single file with those three scales

#### Scenario: Circular include
- **WHEN** `a.json` includes `b.json` and `b.json` includes `a.json`
- **THEN** rules loading fails with a configuration error that names `a.json` and `b.json` and states that the include is circular

#### Scenario: Scale name defined in two files
- **WHEN** two included files both define a scale named `Social_Trust`
- **THEN** rules loading fails with a configuration error naming `Social_Trust` and both files

#### Scenario: Column used in two files
- **WHEN** `core.json` lists `trstprl` in `Trust_Institutions` and an included `extra.json` lists `trstprl` in another scale
- **THEN** rules loading fails with a configuration error naming `trstprl`, both scales, and both files

#### Scenario: Root-only setting in an included file
- **WHEN** an included file defines `flag_threshold`
- **THEN** rules loading fails with a configuration error naming `flag_threshold` and the included file

#### Scenario: Minimum Mahalanobis scales in an included file
- **WHEN** an included file defines `mahalanobis_min_scales`
- **THEN** rules loading fails with a configuration error naming `mahalanobis_min_scales` and the included file

#### Scenario: Invalid minimum Mahalanobis scales
- **WHEN** the root file sets `mahalanobis_min_scales` to `0`, `2.5`, or `"3"`
- **THEN** rules loading fails with a configuration error stating that `mahalanobis_min_scales` must be a positive integer

### Requirement: Declare rule-only variables
The rules MAY define a `variables` object for binary, categorical, count, and year variables that contradiction rules need but that are not scales. Each variable SHALL define numeric `valid_min` and `valid_max` with `valid_min` less than `valid_max`, MAY define `missing_codes` outside that range, and MAY define `module` and `required` with the same meaning and defaults as for scales. Variables SHALL NOT be used by the straightlining or Mahalanobis detectors and SHALL NOT produce `Missing_Value` or `Invalid_Value` markers. A variable value that is a missing code, lies outside the variable's range, or is not numeric SHALL make every rule that references it skipped for that respondent.

#### Scenario: Variable value is a missing code
- **WHEN** the variable `rshipa2` declares `missing_codes` `66`, `77`, `88`, and `99` and a respondent's `rshipa2` is `66`
- **THEN** every rule that references `rshipa2` is skipped for that respondent and the respondent's `data_quality` field does not gain a marker for `rshipa2`

#### Scenario: Variable shares a column with a scale
- **WHEN** a column is listed in a scale and also declared as a variable
- **THEN** rules loading fails with a clear configuration error naming the column

### Requirement: Skip optional scales that are absent from the data
A scale or variable whose `required` is `false` SHALL be skipped when none of its columns is in the input. A skipped scale SHALL not be evaluated by any detector, SHALL not produce a distance column or data-quality markers, and SHALL not count toward any respondent's scale-based penalties. A missing column of a scale or variable whose `required` is `true` SHALL remain a structural error, and an optional scale with some but not all of its columns present SHALL be a structural error that names the scale and its missing columns. A run SHALL fail with a clear structural error when every scale is skipped.

#### Scenario: Rotating module absent
- **WHEN** the rules contain a core scale with `required` `true` and a rotating scale with `required` `false`, and the input contains only the core scale's columns
- **THEN** the run succeeds, the rotating scale is skipped and listed by name in the summary and the report, and every respondent's scale-based penalties are computed from the core scale alone

#### Scenario: Every scale skipped
- **WHEN** every configured scale has `required` `false` and none of their columns is in the input
- **THEN** the command exits with a clear structural error stating that no configured scale is present and does not write a scored output

### Requirement: Derive Mahalanobis thresholds from a significance level
When a scale defines `mahalanobis_alpha`, the system SHALL use as its Mahalanobis threshold the `(1 - mahalanobis_alpha)` quantile of the chi-square distribution whose degrees of freedom equal the scale's item count. The derived threshold SHALL be applied with the same strict comparison as a configured threshold and SHALL be shown in the report with its source.

#### Scenario: Alpha matches the reference threshold
- **WHEN** the five-item `Trust_Institutions` scale sets `mahalanobis_alpha` `0.05` instead of `mahalanobis_threshold` `11.070498`
- **THEN** its threshold rounds to `11.070498` and every respondent receives the same Mahalanobis result as with the configured threshold

#### Scenario: Alpha for a four-item scale
- **WHEN** a four-item scale sets `mahalanobis_alpha` `0.01`
- **THEN** its threshold rounds to `13.276704`

### Requirement: Provide modular ESS round 2 configurations
The repository SHALL ship `config/ess2.json`, which includes `config/ess/core.json`, `config/ess/r2_health.json`, `config/ess/r2_econ_morality.json`, and `config/ess/r2_family_work.json`, sets `id_column` `idno`, `flag_threshold` `50`, and `mahalanobis_min_scales` `3`, and defines the round-specific socio-demographic contradiction rules. Scales in `core.json` SHALL have `module` `core` and `required` `true`; scales and variables in the three `r2_*` files SHALL have `module` `rotating` and `required` `false`. Every ESS scale SHALL set `mahalanobis_alpha` `0.01`, `min_items_straightlining` `5`, and `mahalanobis_min_rows_per_item` `10`, and SHALL list as `missing_codes` the codes that the ESS round 2 SPSS metadata declares as user-missing for its items. Binary and categorical variables, counts, years, and behaviour or event-frequency blocks SHALL NOT be scales; those that rules need SHALL be declared as variables. The existing `config/scale_logic.json` SHALL remain unchanged and keep working.

#### Scenario: Core-only data
- **WHEN** the CLI is run with `config/ess2.json` on synthetic data that contains every core column and no rotating-module column
- **THEN** the run succeeds and the summary lists every rotating scale under `Skipped scales:`

#### Scenario: Real ESS data stays out of the repository
- **WHEN** the repository contents are listed after the change
- **THEN** no real ESS respondent data is present; the ESS round 2 file is used only for manual metadata checks and a manual smoke run outside the repository

### Requirement: Deterministically verify modular configuration and scale-aware scoring
The project SHALL include deterministic tests with synthetic data covering include chains, circular includes, conflicting scale names and columns across files, an absent optional module, an optional scale with partly missing columns, `min_items_straightlining`, alpha-derived thresholds, the minimum valid-row count, and the minimum number of flagged Mahalanobis scales with at least three scales (below, at, and with the default of `1`). The full test suite SHALL contain at least 91 tests.

#### Scenario: Modular and scale-aware behaviour is tested
- **WHEN** the full test suite is run
- **THEN** it passes, includes tests for each listed behaviour with hand-checked expected values, and the pre-existing tests keep their expected scores

### Requirement: Discard input file metadata after loading
After reading a `.csv`, `.xlsx`, or `.sav` input, the system SHALL return a data frame whose `attrs` mapping is empty, so that file-level metadata such as SPSS variable labels, value labels, and missing ranges is not carried into scoring. Discarding this metadata SHALL NOT change any loaded value, column, column order, or data type, and SHALL NOT change any scoring result, summary, scored output, or report.

#### Scenario: SPSS metadata is discarded
- **WHEN** a labeled `.sav` input is loaded
- **THEN** the loaded data frame's `attrs` is empty and the raw numeric codes are unchanged

#### Scenario: SPSS results equal CSV results
- **WHEN** the same responses are scored once from a `.sav` file and once from the equivalent `.csv` file with the same rules
- **THEN** the appended result columns of both scored outputs are identical, and the original columns differ at most in the numeric type SPSS stores them with

#### Scenario: CSV and Excel inputs carry no metadata
- **WHEN** a `.csv` or `.xlsx` input is loaded
- **THEN** the loaded data frame's `attrs` is empty

### Requirement: Score with column-wise operations and unchanged results
The system SHALL compute straightlining, contradiction-rule, and data-quality results with column-wise operations over all respondents instead of indexing a pandas object per respondent. For every input and rules file, the scored output SHALL be byte-identical to the row-by-row implementation it replaces, including every column, its data type, `flag_reasons` content and order, `data_quality` markers, and the `detector_details` JSON text, and the per-scale run facts, console summary, and diagnostic report SHALL be unchanged. The row-level functions `straightlining(row, scales)` and `logical_contradictions(row, rules)` SHALL remain available with unchanged signatures and results.

#### Scenario: Column-wise and row-by-row scoring agree
- **WHEN** a synthetic input that includes mixed text and numeric cells, empty strings, missing codes, out-of-range values, an entirely missing respondent, threshold boundary values, and a `mahalanobis_min_scales` above `1` is scored with the column-wise implementation and with the row-by-row reference
- **THEN** both scored outputs serialise to the same CSV text and the per-scale run facts are equal

#### Scenario: Regression outputs stay byte-identical
- **WHEN** the command-line tool scores `spike_data.csv` with `config/spike_logic.json` and `tests/fixtures/ess_mock.csv` with `config/scale_logic.json`, with `--report`
- **THEN** the console summaries, scored CSV files, and report files are byte-identical to those produced before the change

#### Scenario: Row-level detector functions are preserved
- **WHEN** `run_spike.py` is run and the existing tests call `straightlining` and `logical_contradictions` with a single respondent row
- **THEN** the `run_spike.py` output is unchanged and the existing tests pass without modification

### Requirement: Deterministically verify fast scoring
The project SHALL include deterministic tests with synthetic or public fixture data that compare the column-wise scoring with the row-by-row reference and check that loaded inputs carry no metadata. These tests SHALL NOT assert wall-clock time limits. The full test suite SHALL contain at least 162 tests, and no pre-existing test SHALL be modified.

#### Scenario: Fast scoring is tested without timing assertions
- **WHEN** the full test suite is run
- **THEN** it passes with at least 162 tests, includes the equivalence and metadata tests, and contains no assertion on elapsed time
