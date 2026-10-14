## Context

The loader currently exposes a CSV-only function and the CLI passes its result directly into the unchanged scoring pipeline. The scoring output already contains the trigger flags, availability fields, score values, and reason text needed for a report. See the proposal for the motivation and the delta spec for the externally visible contract.

## Goals / Non-Goals

**Goals:**

- Centralize extension dispatch in the input layer so all supported formats receive identical structural validation.
- Preserve the current `DataFrame`-based scoring API and the current CSV output contract.
- Add a report writer that derives every value from the scored `DataFrame`, with stable headings, ordering, formatting, and explicit write errors.
- Pin the two format-reader dependencies and add focused deterministic coverage.

**Non-Goals:**

- No changes to detector formulas, thresholds, weights, aggregation, or row-level missing-value semantics.
- No XLSX or SPSS output format; scored results remain CSV.
- No changes to rules-file schema or a new report configuration file.

## Decisions

1. **Use one extension-dispatch loader.** The CLI will call a format-agnostic loader that normalizes the suffix case and dispatches to `pandas.read_csv`, `pandas.read_excel`, or `pandas.read_spss`. The pandas SPSS reader is backed by the pinned `pyreadstat` dependency and exposes the required `convert_categoricals=False` option. This avoids format checks in the CLI and keeps missing-column/id validation in one place. A format-specific set of public loader functions was considered, but would duplicate validation and make future formats inconsistent.

2. **Read SPSS with raw codes.** The SAV branch will call `read_sav` with `convert_categoricals=False`, preserving numeric codes for all detectors. Using the default conversion was rejected because value-label strings would make numeric detector inputs invalid.

3. **Keep report generation separate from scoring.** A reporting helper will accept the scored frame and output path, compute aggregate counts and percentages from the three existing trigger columns, and select rows with `suspicious` or non-empty `flag_reasons`. This leaves the scoring core untouched and makes the report unit-testable without launching the CLI.

4. **Define deterministic report formatting.** The report will use fixed section headings, two-decimal percentages and scores, a stable detector order, and escaped Markdown table cell content. Respondents will be ordered by ascending available `quality_score` with stable input order as the tie-breaker; when no id column is configured, the row number is used.

5. **Surface filesystem errors through the existing CLI error path.** Input-reader and report-writer failures will be converted to the repository's validation/error type with the path and operation in the message. The CLI will not produce a success-shaped fallback when a requested report cannot be written.

6. **Pin compatible reader versions.** `openpyxl` and `pyreadstat` will be added to `requirements.txt` with exact `==` versions, matching the project's existing pinned-dependency convention. Tests will create small temporary XLSX files and a deterministic SAV fixture or generated SAV file without committing private data.

## Risks / Trade-offs

- [Risk] Excel/SPSS readers can infer unexpected dtypes → Mitigation: validate required headers after loading and explicitly test numeric detector inputs, especially SPSS value labels.
- [Risk] Large reports may contain many flagged respondents → Mitigation: report all flagged rows in a compact deterministic table while keeping the report generation linear in the scored frame.
- [Risk] Existing inputs may use uppercase suffixes → Mitigation: dispatch on a lowercased `Path.suffix`.
- [Risk] A report path may be a directory or have an unwritable parent → Mitigation: create parent directories consistently and raise a clear `DataValidationError` on write failure.

## Migration Plan

1. Install the newly pinned dependencies from `requirements.txt`.
2. Deploy the loader, report helper, CLI option, documentation, and tests together.
3. Existing CSV invocations remain unchanged; users opt into reports with `--report`.
4. Rollback consists of reverting the code and dependency additions; existing scored CSV behavior remains the compatibility baseline.
