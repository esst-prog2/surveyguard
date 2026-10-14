## 1. Input loading

- [x] 1.1 Add exact `openpyxl` and `pyreadstat` pins to `requirements.txt`, install from the manifest, and verify both readers import successfully.
- [x] 1.2 Replace the CSV-only CLI loading call with extension-dispatched loading for `.csv`, `.xlsx`, and `.sav`, including shared question/id validation and explicit unsupported-extension errors; verify existing CSV tests remain green and unit tests cover uppercase suffixes and missing columns.
- [x] 1.3 Configure SAV loading to preserve raw numeric codes with `convert_categoricals=False`, generate a deterministic labeled-code fixture, and verify the resulting detector input contains codes rather than value-label strings.

## 2. Diagnostic reporting

- [x] 2.1 Implement a reporting helper that writes deterministic Markdown aggregate sections, detector counts/percentages, and a stable flagged/most-suspicious respondent table with exact reason text; verify unit tests for empty, clean, flagged, and tied-score frames.
- [x] 2.2 Add the optional `--report` CLI argument, invoke report generation only after successful scoring/output, and route report write failures through the existing explicit error handling; verify CLI tests for creation, replacement, reason content, percentages, and unwritable paths.

## 3. Documentation and regression coverage

- [x] 3.1 Extend `README.md` with `.xlsx`/`.sav` usage, the raw-code SPSS rule, report invocation, and report contents; verify examples match the implemented CLI flags and output behavior.
- [x] 3.2 Run the focused loader/report unit and CLI tests, then the full `python -m pytest -q` suite, and verify the original scoring values and CSV output contract are unchanged.
