2026-09-22 - We started the MVP - Me
2026-09-22 - Installed Node.js 20.20.2, selected @fission-ai/openspec 1.13.0, and initialized OpenSpec for GitHub Copilot - Copilot
2026-09-22 - Each detector will have its own configurable weight in the quality score - User
2026-09-22 - Missing responses remain in the output with a Missing_Value marker; Mahalanobis is not calculated for those rows, and other detectors use available values - User
2026-09-22 - All future decisions must be recorded in the planning log - User
2026-09-22 - The quality_score ranges from 0 to 100, where 100 is good quality and 0 is the most suspicious response; lower scores are worse - User
2026-09-22 - A configurable flag_threshold determines suspicious status from the aggregate score, while detector-specific flag_reasons remain visible - User
2026-09-22 - Survey questions are identified by CSV header names in the JSON configuration, independent of column order - User
2026-09-22 - Likert scale minimum and maximum values are configurable per question block - User
2026-09-22 - Inverted-item contradictions are detected when both values fall in the configured high range or both fall in the configured low range; middle values alone do not trigger a contradiction - User
2026-09-22 - Configuration and structural errors fail fast, row-level invalid or missing values are marked and processing continues, and mathematical failures produce controlled error messages - User
2026-09-22 - The CLI supports an optional --output path; without it, the output filename is derived by changing the input suffix to _scored.csv - User
2026-09-22 - The console summary includes processed count, suspicious count, per-detector counts, missing/invalid counts, score statistics, and output path - User
2026-09-22 - The MVP includes unit tests for each detector, error-handling tests, and a CLI integration test using small fixtures - User
2026-09-22 - pytest is the MVP test framework, with fixture data stored separately from production input data - User
2026-09-22 - The MVP targets Python 3.10+, uses pandas, numpy, scipy, and pytest, and pins dependencies in requirements.txt - User
2026-09-22 - Initial detector weights are 1.0 each and the default flag_threshold is 50; both remain configurable in JSON - User
2026-09-22 - The scored CSV preserves all original columns and appends auditable quality, status, reason, detector-result, and data-quality fields - User
2026-09-22 - An optional id_column identifies respondent IDs; IDs and other non-question metadata are preserved but excluded from all statistics - User
2026-09-22 - Repository demonstrations and tests use only synthetic or public anonymized data; real PII and proprietary data are excluded - User
2026-09-22 - Each detector emits a normalized penalty from 0 to 1; quality_score is 100 times one minus the detector-weighted average penalty - Copilot
2026-09-22 - The JSON configuration groups question columns into named blocks and stores block ranges, inverted pairs, detector weights, detector thresholds, flag_threshold, and optional id_column - Copilot
2026-09-30 - The spike evaluation uses EXT1/EXT2 and EXT3/EXT4 as explicit test pairs because spike_data.csv has no semantic pair metadata - Copilot
2026-09-30 - We measured it: the Mahalanobis D^2 threshold is 23.843516, because it flags exactly 50 of 1,000 spike respondents and therefore produces the requested 5% rate - User
2026-10-03 - Set logical-contradiction weight to zero pending validation against labeled clean responses; retain its diagnostic reasons - User
2026-10-03 - The initial 10-item clean spike rates were 0.2% straightlining, 25.4% logical contradiction, and 71.9% Mahalanobis at D^2=6 - User
2026-10-03 - Calibrate the deployed Mahalanobis threshold on the four-item EXT1-EXT4 spike slice; measured D^2=9.829530 for exactly 5% (50/1,000) - Copilot
2026-10-03 - Set logical-contradiction weight to zero pending validation against labeled clean responses; retain its diagnostic reasons - User
2026-10-09 - A test would go red if the Mahalanobis detector flags a number of clean respondents different from exactly 50 (5%) out of the 1000 rows in spike_data.csv at the **9.829530** threshold. The expected value (50) comes from last week's external Spike measurement, not from running the code - User
2026-10-09 - Added a real-world regression test for Mahalanobis on EXT1-EXT4 in spike_data.csv and recorded the deliberate red run. Temporarily changed the configured threshold to 100.0; command: `python -m pytest -q tests/test_real_world.py`. Terminal output:
	```text
	F                                                                        [100%]
	================================== FAILURES ===================================
	___________ test_mahalanobis_flags_exactly_fifty_spike_respondents ____________

			def test_mahalanobis_flags_exactly_fifty_spike_respondents():
					responses = pd.read_csv(ROOT / "spike_data.csv")
					rules = load_rules(ROOT / "config" / "scale_logic.json")
					columns = ("EXT1", "EXT2", "EXT3", "EXT4")

					_, flagged = mahalanobis(
							responses,
							columns,
							threshold=rules.thresholds["mahalanobis_outlier"],
					)

					assert len(responses) == 1000
	>       assert int(flagged.sum()) == 50
	E       assert 0 == 50
	E        +  where 0 = int(np.int64(0))
	E        +    where np.int64(0) = sum()
	E        +      where sum = 0      False\n1      False\n2      False\n3      Fal\n       ...  \n995    False\n996    False\n997    False\n998    False\n999    False\nLength: 1000, dtype: bool.sum

	tests\\test_real_world.py:24: AssertionError
	=========================== short test summary info ===========================
	FAILED tests/test_real_world.py::test_mahalanobis_flags_exactly_fifty_spike_resp
	ondents - assert 0 == 50
	1 failed in 4.14s
	```
2026-10-09 - Restored the correct Mahalanobis threshold to 9.829530 and reran `python -m pytest -q tests/test_real_world.py`. Successful terminal result: `1 passed in 0.84s` - Copilot
2026-10-09 - Repeated the deliberate red run with `python -m pytest -q --tb=line tests/test_real_world.py`; terminal output excerpt: `F [100%]`, `E assert 0 == 50`, `tests\test_real_world.py:24: assert 0 == 50`, `1 failed in 0.78s` - Copilot
2026-10-09 - Final green verification with the calibrated threshold restored: `python -m pytest -q tests/test_real_world.py` -> `1 passed in 0.82s` - Copilot
2026-10-09 - We expect the CLI to successfully process spike_data.csv and flag exactly 50 rows via the Mahalanobis detector based on our calibration. - User
2026-10-09 - Ran `python detect_anomalies.py spike_data.csv --rules config/scale_logic.json`. Actual output: `Error: Missing configured id column: respondent_id`. The CLI stopped before scoring; `spike_scored.csv` was not created. The input contains EXT1-EXT10 but no respondent_id column - Copilot
2026-10-09 - The CLI failed because spike_data.csv lacks the configured respondent_id column. Following instructions, I removed the id_column requirement from the config to allow execution. - User
2026-10-09 - After removing id_column, the CLI reported missing configured question columns Q1-Q4. Updated the configured four-item block to EXT1-EXT4 and its inverted pair to EXT2/EXT3 to match the Spike dataset and the calibrated slice - Copilot
2026-10-09 - Successful CLI run: `python detect_anomalies.py spike_data.csv --rules config/scale_logic.json`. Actual output: Processed 1000; Suspicious 3; Straightlining 21; Logical contradiction 143; Mahalanobis outlier 50; Missing/invalid 0; Average quality score 96.45; Minimum quality score 0.00; Output `spike_data_scored.csv`. Confirmed the output file exists - Copilot
2026-10-13 - Audited the codebase and requirements: removed unused SciPy and unused imports (`PairConfig`, `os`, and test-only `numpy`); all functions in `surveyguard` are referenced and no duplicate detector behavior was found. Pinned used packages exactly, with Python-version markers preserving Python 3.10+; Pylance reported no remaining diagnostics. `python -m pytest -q` on Python 3.14.3: 16 passed in 8.65s - Copilot
2026-10-13 - Audited `surveyguard` and `detect_anomalies.py`: found no swallowed/bare exceptions or error-path `return None`; intentional catches wrap/report specific expected errors. Made `thresholds.mahalanobis_outlier` required because the scoring fallback of 0.0 was undocumented and silently altered behavior; retained documented optional settings/defaults. Added tests for missing threshold object/member; pytest verification pending - Copilot
2026-10-13 - Follow-up verification for the configuration/error-handling audit: `python -m pytest -q` on Python 3.14.3 -> 18 passed in 5.45s; Pylance workspace diagnostics empty; `git diff --check` clean - Copilot
2026-10-13 - Compared the active OpenSpec requirements and archived design with `surveyguard` and tests. Specified detector math (population IRV, sample-covariance Mahalanobis D^2, strict threshold comparison, inclusive contradiction bands), score formula, and implemented optional-setting defaults in the active spec. Added deterministic tests with hand-computed IRV, Mahalanobis distances/boundary, contradiction reasons/penalties, and weighted score. `python -m pytest -q` on Python 3.14.3: 21 passed. Found an unresolved archived-design mismatch: unavailable detector results still contribute zero penalty at their configured weight; behavior when every detector is unavailable is unspecified. Awaiting user direction before changing score semantics - Copilot
2026-10-13 - User chose to exclude unavailable detectors from each respondent's weighted score and leave both quality_score and suspicious empty when no positive-weight detector is available. Added availability tracking/output fields, nullable score/status, and a Not scored summary count; updated active OpenSpec and tests. Final `python -m pytest -q` on Python 3.14.3: 25 passed; Pylance diagnostics empty - Copilot
2026-10-13 - Updated README usage/behavior notes for detector availability, blank unscored results, and the Not scored summary count - Copilot
2026-10-13 - Audited `git ls-files`; removed tracked Python bytecode caches and generated `spike_data_scored.csv` from the index while preserving `spike_data.csv`, source, fixtures, specs, and configuration. Added `.gitignore` rules for Python/test caches, build/environment artifacts, and generated `*_scored.csv` files - Copilot
2026-10-14 - Applied the OpenSpec change `extend-inputs-and-diagnostics`; preserved the existing scoring and detector core and limited the implementation to input loading, reporting, dependencies, documentation, tests, and specifications - Copilot
2026-10-14 - Added exact dependency pins `openpyxl==3.1.5` and `pyreadstat==1.3.6` to `requirements.txt`, installed them from the manifest, and verified both packages import successfully on Python 3.14.3 - Copilot
2026-10-14 - Replaced the CSV-only CLI loading path with extension-based loading for `.csv`, `.xlsx`, and `.sav`, including shared question/id validation, case-insensitive suffix handling, and explicit unsupported-extension errors - Copilot
2026-10-14 - Used `pandas.read_spss(..., convert_categoricals=False)` for SPSS input because pyreadstat 1.3.6 `read_sav` does not accept the `convert_categoricals` argument; this preserves raw numeric SPSS codes instead of value-label text - Copilot
2026-10-14 - Added deterministic loader tests for uppercase Excel extensions, Excel data, labeled SPSS files, raw numeric SPSS values, and unsupported input extensions - Copilot
2026-10-14 - Added the optional CLI option `--report <path.md>` and a deterministic Markdown report containing processed/suspicious counts, average/minimum quality scores, detector counts and percentages, and flagged respondent reasons - Copilot
2026-10-14 - Defined report ordering as ascending quality score with stable input-order tie breaking, escaped Markdown table cells, and explicit report-write errors through the existing user-facing error path - Copilot
2026-10-14 - Added report unit and CLI tests for empty, clean, flagged, tied-score, report-content, percentage, replacement, unsupported-input, and report-path failure cases - Copilot
2026-10-14 - Updated README usage documentation for `.xlsx` and `.sav` inputs, raw SPSS codes, and Markdown diagnostic reports - Copilot
2026-10-14 - Focused loader and CLI verification passed: 32 tests; after adding direct XLSX/SAV CLI coverage, the CLI suite passed 6 tests and the full suite passed 34 tests - Copilot
2026-10-14 - Python syntax/bytecode validation with `python -m compileall -q surveyguard detect_anomalies.py` passed - Copilot
2026-10-14 - Synced the `survey-quality-detection` delta into the main OpenSpec specification, preserving existing detector requirements and adding supported input formats, raw SPSS-code behavior, diagnostic reporting, and deterministic verification requirements - Copilot
2026-10-14 - Added testable scenarios for the pre-existing optional configuration defaults and precise scoring defaults so the main specification passes strict validation - Copilot
2026-10-14 - Strict validation passed for the synchronized main spec and the complete change; all 7 implementation tasks were marked complete - Copilot
2026-10-14 - Archived the completed OpenSpec change as `openspec/changes/archive/2026-10-14-extend-inputs-and-diagnostics`; the archive command confirmed the main specs were already synchronized and no active changes remain - Copilot
2026-10-14 - Manually tested the CLI with `--report` on `.xlsx` and `.sav` files generated from `spike_data.csv`. Both runs processed exactly 1,000 respondents, marked 3 as suspicious, reported an average quality score of 96.45, and counted 50 Mahalanobis outliers (5.00%); the generated Markdown reports were byte-for-byte identical and contained the same results - Copilot
2026-10-14 - Deleted the generated XLSX/SAV test data, scored CSV outputs, Markdown reports, and temporary validation directory after verification, in accordance with the lesson's data-cleanup requirement - Copilot
