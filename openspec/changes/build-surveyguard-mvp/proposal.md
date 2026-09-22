## Why

SurveyGuard currently has a documented MVP goal but no implementation or durable behavioral contract. The project needs a reproducible CLI that can score numeric survey responses for careless-responding signals without requiring a GUI, proprietary data, or opaque machine learning.

## What Changes

- Add a Python 3.10+ command-line application that reads numeric survey responses from CSV and detector metadata from JSON.
- Add deterministic straightlining detection using intra-individual response variability (IRV) over configured question blocks.
- Add Mahalanobis-distance detection for multivariate response outliers, with controlled handling for missing values and singular covariance matrices.
- Add configurable inverted-item contradiction checks using per-block Likert ranges and high/low contradiction bands.
- Add configurable detector weights, score normalization, and a `flag_threshold` for the aggregate `suspicious` status.
- Preserve all original CSV columns and append auditable quality, status, reason, detector-result, and data-quality fields.
- Add an optional `--output` path with automatic `_scored.csv` naming when omitted.
- Print a summary containing processed, suspicious, per-detector, missing/invalid, score-statistic, and output-path information.
- Add fail-fast validation for configuration and CSV structure, row-level markers for bad values, and controlled mathematical errors.
- Add `pytest` unit, error-handling, and CLI integration tests with synthetic fixtures.
- Keep demonstrations and tests limited to synthetic or public anonymized data; do not add PII or proprietary data.

## Capabilities

### New Capabilities

- `survey-quality-detection`: Detect careless or anomalous numeric survey responses, calculate an auditable quality score, and expose the results through a reproducible CLI and scored CSV.

### Modified Capabilities

- None.

## Impact

- New Python source modules for CSV/configuration handling, detector calculations, score aggregation, validation, and CLI orchestration.
- New `config/`, `data/`, `output/`, and `tests/` project areas, including `requirements.txt` and synthetic fixtures.
- Runtime dependencies: pandas, numpy, scipy, and pytest.
- New CLI contract centered on `python detect_anomalies.py <input.csv> --rules <rules.json> [--output <output.csv>]`.
- No GUI, browser service, NLP, unsupervised ML, or automated respondent deletion is introduced.