## ADDED Requirements

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
