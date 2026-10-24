## MODIFIED Requirements

### Requirement: Spike rules file preserves the calibrated results
The repository SHALL ship the spike calibration rules as `config/spike_logic.json` in the scale-based rules schema: one scale over `EXT1`, `EXT2`, `EXT3`, and `EXT4` with `valid_min` `1`, `valid_max` `5`, `irv_threshold` `0`, and `mahalanobis_threshold` `9.829530`, plus the former `EXT2`/`EXT3` inverted pair expressed as two contradiction rules (both items `>= 4`, and both items `<= 2`) with a `logical_contradiction` weight of `0`. Applying this threshold to the squared Mahalanobis distances of `EXT1` through `EXT4` over all 1000 rows of `spike_data.csv` SHALL flag exactly 50 respondents. Running the CLI on `spike_data.csv` with this file SHALL report the same counts as the pre-change CLI run with the former `config/scale_logic.json`: 1000 processed, 2 suspicious, 181 detector-triggered, 20 straightlining, 140 logical contradiction, 47 Mahalanobis outlier, 0 missing, 13 invalid, 13 not scored, average quality score `96.61`, and minimum quality score `0.00`. Because the file defines a single scale and leaves `mahalanobis_min_scales` at its default of `1`, the modular configuration and scale-aware scoring features SHALL leave its console summary and its scored CSV byte-identical to the output before those features were introduced; only the Markdown report gains the scale results and skipped scales and rules sections.

#### Scenario: Fifty spike respondents exceed the calibrated threshold
- **WHEN** the squared Mahalanobis distances of `EXT1` through `EXT4` are calculated over all 1000 rows of `spike_data.csv` and compared with the `mahalanobis_threshold` read from `config/spike_logic.json`
- **THEN** exactly 50 respondents have a distance strictly greater than the threshold

#### Scenario: CLI summary on the spike data is unchanged
- **WHEN** `python detect_anomalies.py spike_data.csv --rules config/spike_logic.json` is run
- **THEN** every count and score statistic in the console summary equals the pre-change values listed in this requirement, the summary contains no `Skipped scales:` line, and its text is byte-identical to the summary printed before the modular configuration and scale-aware scoring features

#### Scenario: Spike scored output is unchanged
- **WHEN** `python detect_anomalies.py spike_data.csv --rules config/spike_logic.json --output <path>` is run before and after the modular configuration and scale-aware scoring features
- **THEN** the two scored CSV files are byte-identical
