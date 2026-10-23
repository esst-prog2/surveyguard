# spike-tooling Specification

## Purpose

Defines the observable behavior of the repository's preparation and calibration scripts that produce and evaluate the spike dataset outside the `surveyguard` package, so that calibration results are verifiable and data-preparation failures are never reported as success.

## Requirements

### Requirement: Exact five-percent calibration threshold
The calibration step SHALL ignore missing distance values, sort the remaining values, set the target count to `floor(n * 0.05)` where `n` is the number of remaining values, and return the arithmetic mean of the largest value outside the target set and the smallest value inside it. Exactly `target` values are then strictly greater than the returned threshold.

#### Scenario: Hand-computed threshold for twenty values
- **WHEN** the distances are the integers `1` through `20`
- **THEN** the target count is `1` and the threshold is exactly `19.5`, the mean of `19` and `20`

#### Scenario: Missing distances are ignored
- **WHEN** the distances are the integers `1` through `20` plus one missing value
- **THEN** the threshold is exactly `19.5`

### Requirement: Reject impossible calibration targets
The calibration step SHALL raise a `ValueError` instead of returning a threshold when no threshold can isolate exactly five percent of the values.

#### Scenario: Tie at the five-percent boundary
- **WHEN** the distances are the integers `1` through `18` followed by `20` and `20`, so that the two largest values are equal
- **THEN** a `ValueError` is raised stating that tied values make an exact 5% threshold impossible

#### Scenario: Too few values for a five-percent target
- **WHEN** fewer than 20 non-missing distances are provided
- **THEN** a `ValueError` is raised stating that the dataset must contain enough rows for a 5% target

### Requirement: Data preparation reports failure through its exit status
The data-preparation script SHALL exit with status `0` only after writing the spike dataset. When the download, archive extraction, file reading, column selection, or file writing fails, the script SHALL print an error message that names the failure and exit with status `1`. Unexpected errors SHALL stop the script with a non-zero status and SHALL NOT be suppressed.

#### Scenario: Network failure
- **WHEN** the dataset download fails with a network error
- **THEN** the script prints an error message and exits with status `1`

#### Scenario: Corrupt archive
- **WHEN** the downloaded content is not a valid ZIP archive
- **THEN** the script prints an error message and exits with status `1`

#### Scenario: Archive without a data table
- **WHEN** the archive contains no `.csv` or `.tsv` file
- **THEN** the script prints an error message stating that no data table was found and exits with status `1`

#### Scenario: Required columns missing
- **WHEN** the data table lacks any of the columns `EXT1` through `EXT10`
- **THEN** the script prints an error message naming the missing columns and exits with status `1`

#### Scenario: Unexpected error is not swallowed
- **WHEN** an error outside the expected failure categories occurs
- **THEN** the error propagates and the process exits with a non-zero status

### Requirement: Data preparation output guarantees
On success, the data-preparation script SHALL write exactly 1000 rows with no missing values in the columns `EXT1` through `EXT10`. It SHALL fail with status `1` and leave any existing spike dataset unchanged when fewer than 1000 complete rows are available or when any earlier step fails.

#### Scenario: Successful preparation
- **WHEN** the archive contains a tab-separated table with at least 1000 complete rows for `EXT1` through `EXT10`
- **THEN** the script writes a spike dataset with exactly those 10 columns and 1000 rows, and exits with status `0`

#### Scenario: Not enough complete rows
- **WHEN** fewer than 1000 rows have complete `EXT1` through `EXT10` values
- **THEN** the script prints an error message stating the available row count, exits with status `1`, and does not write the spike dataset

### Requirement: Spike rules file preserves the calibrated results
The repository SHALL ship the spike calibration rules as `config/spike_logic.json` in the scale-based rules schema: one scale over `EXT1`, `EXT2`, `EXT3`, and `EXT4` with `valid_min` `1`, `valid_max` `5`, `irv_threshold` `0`, and `mahalanobis_threshold` `9.829530`, plus the former `EXT2`/`EXT3` inverted pair expressed as two contradiction rules (both items `>= 4`, and both items `<= 2`) with a `logical_contradiction` weight of `0`. Applying this threshold to the squared Mahalanobis distances of `EXT1` through `EXT4` over all 1000 rows of `spike_data.csv` SHALL flag exactly 50 respondents. Running the CLI on `spike_data.csv` with this file SHALL report the same counts as the pre-change CLI run with the former `config/scale_logic.json`: 1000 processed, 2 suspicious, 181 detector-triggered, 20 straightlining, 140 logical contradiction, 47 Mahalanobis outlier, 0 missing, 13 invalid, 13 not scored, average quality score `96.61`, and minimum quality score `0.00`.

#### Scenario: Fifty spike respondents exceed the calibrated threshold
- **WHEN** the squared Mahalanobis distances of `EXT1` through `EXT4` are calculated over all 1000 rows of `spike_data.csv` and compared with the `mahalanobis_threshold` read from `config/spike_logic.json`
- **THEN** exactly 50 respondents have a distance strictly greater than the threshold

#### Scenario: CLI summary on the spike data is unchanged
- **WHEN** `python detect_anomalies.py spike_data.csv --rules config/spike_logic.json` is run
- **THEN** every count and score statistic in the console summary equals the pre-change values listed in this requirement

### Requirement: Spike evaluation output is unchanged
The spike evaluation script SHALL express its `EXT1`/`EXT2` and `EXT3`/`EXT4` test pairs as explicit high-high (`>= 4` on both items) and low-low (`<= 2` on both items) contradiction rules on a `1`-to-`5` scale, and SHALL print the same five lines and values as before the change: straightlining `2.1%`, logical contradiction `25.4%`, Mahalanobis at the legacy threshold `6` `15.7%`, calibrated threshold `9.829530`, and `5.0%` at the calibrated threshold.

#### Scenario: Spike evaluation run
- **WHEN** `python run_spike.py` is run on the committed `spike_data.csv`
- **THEN** its output is identical to the pre-change output
