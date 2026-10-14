## MODIFIED Requirements

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

## ADDED Requirements

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
