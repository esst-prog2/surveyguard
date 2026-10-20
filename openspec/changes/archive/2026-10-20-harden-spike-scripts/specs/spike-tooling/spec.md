## Purpose

Defines the observable behavior of the repository's preparation and calibration scripts that produce and evaluate the spike dataset outside the `surveyguard` package, so that calibration results are verifiable and data-preparation failures are never reported as success.

## ADDED Requirements

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
