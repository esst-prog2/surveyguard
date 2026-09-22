## 1. Project Setup

- [ ] 1.1 Add the Python package/module layout for CLI orchestration, configuration validation, detectors, scoring, IO, and reporting; verify imports resolve from a clean checkout.
- [ ] 1.2 Add `requirements.txt` with Python 3.10+ compatible pandas, numpy, scipy, and pytest dependencies; verify installation in a clean virtual environment.
- [ ] 1.3 Add documented synthetic CSV and JSON fixtures under the test-data area; verify no fixture contains PII or proprietary data.

## 2. Configuration and Input Validation

- [ ] 2.1 Implement JSON schema parsing for optional `id_column`, named question blocks, per-block ranges and bands, inverted pairs, detector thresholds, weights, and `flag_threshold`; verify valid and malformed configurations with unit tests.
- [ ] 2.2 Implement CSV header validation and metadata/question-column separation; verify missing configured columns fail before output creation.
- [ ] 2.3 Implement row-level numeric conversion and missing/invalid markers without imputation; verify affected rows remain in the output and unavailable calculations are explicit.

## 3. Detector Calculations

- [ ] 3.1 Implement IRV calculation and straightlining rule evaluation per configured block; verify constant ten-item rows return IRV `0` and the expected reason.
- [ ] 3.2 Implement inverted-pair high-high and low-low contradiction checks using block ranges and configured bands; verify high, low, and middle scenarios.
- [ ] 3.3 Implement Mahalanobis distance, centroid distance, normalized outlier penalty, and missing-row exclusion; verify centroid distance is exactly `0`.
- [ ] 3.4 Convert singular covariance failures into a controlled domain error with actionable text; verify the singular-matrix test does not expose a native exception.

## 4. Scoring and Output

- [ ] 4.1 Implement structured detector results with normalized penalties and reasons; verify each result exposes trigger state, penalty, and relevant details.
- [ ] 4.2 Implement weighted score aggregation using `100 * (1 - weighted_average_penalty)`, clamped to `0`-`100`, with default weights `1.0`; verify default and custom-weight cases.
- [ ] 4.3 Implement `suspicious` classification from configurable `flag_threshold` and preserve all detector reasons; verify a score below `50` is suspicious by default.
- [ ] 4.4 Implement scored CSV writing that preserves original columns and appends quality, status, reasons, detector, and data-quality fields; verify explicit and derived `_scored.csv` paths.
- [ ] 4.5 Implement stable console summary output containing counts, detector totals, missing/invalid totals, score statistics, and output path; verify labels with the CLI integration test.

## 5. CLI and Documentation

- [ ] 5.1 Implement `detect_anomalies.py <input.csv> --rules <rules.json> [--output <output.csv>]` with non-zero exits for configuration, structure, and mathematical failures; verify help and failure-path behavior.
- [ ] 5.2 Document the JSON configuration shape, score formula, output columns, error policy, privacy boundary, and CLI examples in `README.md`; verify examples match the implemented command.

## 6. Tests and Verification

- [ ] 6.1 Add pytest unit tests for configuration validation, IRV, inverted pairs, Mahalanobis, score aggregation, and metadata preservation; verify the complete unit suite passes.
- [ ] 6.2 Add pytest error-handling tests for missing columns, malformed rules, invalid row values, missing values, and singular matrices; verify controlled outcomes.
- [ ] 6.3 Add a CLI integration test using synthetic fixtures that checks output rows/columns, automatic output naming, summary content, and suspicious counts; verify it passes in a clean environment.
- [ ] 6.4 Run the full pytest suite and a representative CLI command from a clean virtual environment; verify both complete successfully and record the result in the change review.