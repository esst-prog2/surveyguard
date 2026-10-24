## MODIFIED Requirements

### Requirement: Accept uploaded inputs
The web interface SHALL provide, in a sidebar that is separate from the main results area, one upload control for the response data file that accepts `.csv`, `.xlsx`, and `.sav` files, a rules source selection, and the "Run SurveyGuard" action. The rules source selection SHALL offer an upload control for a `.json` rules file and a choice of the bundled rules files in the repository's `config` folder (top level only, for example `config/ess2.json`, `config/scale_logic.json`, and `config/spike_logic.json`). The run action SHALL be unavailable until the response data file has been provided and either a rules file has been uploaded or a bundled rules file has been chosen. The main area SHALL be reserved for guidance, run feedback, and results.

#### Scenario: Both files are required
- **WHEN** the interface is opened and the response data file, the rules, or both are still missing
- **THEN** the "Run SurveyGuard" action cannot be triggered and the sidebar tells the user which input is still missing

#### Scenario: Run becomes available
- **WHEN** a supported response file has been uploaded and either a `.json` rules file has been uploaded or a bundled rules file has been chosen
- **THEN** the "Run SurveyGuard" action can be triggered

#### Scenario: Controls live in the sidebar
- **WHEN** the interface is opened
- **THEN** the upload controls, the rules source selection, and the "Run SurveyGuard" action are in the sidebar, and the main area shows a hint to provide the inputs in the sidebar instead of results

### Requirement: Display interactive result tables
After a successful run, the web interface SHALL display an interactive detector-results table with one row per detector (straightlining, contradiction, Mahalanobis) showing its trigger count and its percentage of processed respondents. It SHALL display an interactive scale-results table with the same rows and values as the scale results table of the diagnostic report, and, when optional scales or rules were skipped, it SHALL name them. It SHALL also display an interactive table of detector-flagged respondents, meaning respondents who are suspicious or have at least one detector reason, showing the respondent identifier (or the 1-based row number when no identifier column is configured), the quality score, whether the respondent is suspicious, and the flag reasons, in the same order as the diagnostic report. A "Show suspicious respondents only" switch above the flagged table SHALL be off by default; when it is on, the table SHALL show only the rows whose `Suspicious` value is true, in the same relative order, and the full table SHALL return when it is switched off. Changing the switch SHALL NOT rerun the analysis or discard the results.

#### Scenario: Detector table matches the report
- **WHEN** a run completes
- **THEN** each detector's count and percentage in the table equal the values in the report's detector table

#### Scenario: Scale table matches the report
- **WHEN** a run completes on `tests/fixtures/ess_mock.csv` with `config/scale_logic.json`
- **THEN** the scale-results table has one row each for `Trust_Institutions` and `Satisfaction` with the same item counts, thresholds, valid rows, straightlining counts, Mahalanobis counts, and statuses as the report

#### Scenario: Skipped scales are named
- **WHEN** a run with `config/ess2.json` skips optional rotating scales because their columns are absent
- **THEN** the interface names every skipped scale and every skipped contradiction rule

#### Scenario: Flagged respondents table
- **WHEN** one or more respondents are suspicious or have detector reasons
- **THEN** the flagged table lists exactly those respondents, ordered by ascending quality score with input order breaking ties and unscored respondents last, with their exact reason text

#### Scenario: Nothing flagged
- **WHEN** no respondent is suspicious or detector-flagged
- **THEN** the interface states that no respondents were flagged instead of showing an empty table

#### Scenario: Filter to suspicious respondents
- **WHEN** the flagged table contains both suspicious and non-suspicious respondents and the user turns on "Show suspicious respondents only"
- **THEN** only the suspicious rows remain, in their original order, and turning the switch off shows all flagged rows again

#### Scenario: Filter with no suspicious respondents
- **WHEN** respondents are flagged but none is suspicious and the switch is on
- **THEN** the interface states that no respondents are suspicious instead of showing an empty table

### Requirement: Report expected failures without crashing
When the rules or the response file are invalid (unreadable JSON, invalid rule definitions, an uploaded rules file that uses `include`, unreadable data, or missing configured columns), the web interface SHALL show a single error message beginning with `Error:` that contains the same explanation the command-line tool prints (or, for an uploaded rules file that uses `include`, states that includes are not supported for uploaded rules and that a bundled rules file or the command-line tool should be used), SHALL NOT show a traceback for these failures, and SHALL NOT show results from a previous run as if they belonged to the new inputs.

#### Scenario: Invalid rules file
- **WHEN** the uploaded rules file is not valid JSON
- **THEN** the interface shows an `Error:` message explaining that the rules JSON could not be read and shows no metrics or tables

#### Scenario: Uploaded rules file with include
- **WHEN** the uploaded rules file contains an `include` list
- **THEN** the interface shows an `Error:` message stating that `include` is not supported for uploaded rules files and pointing to the bundled rules files and the command-line tool, and shows no metrics or tables

#### Scenario: Missing configured columns
- **WHEN** the response file lacks a question column named in a required scale
- **THEN** the interface shows an `Error:` message naming the missing columns and shows no metrics or tables

#### Scenario: Inputs changed after a run
- **WHEN** the user replaces the uploaded data file, replaces the uploaded rules file, or chooses a different rules source after a successful run
- **THEN** the previous run's results are no longer displayed until the run action is triggered again

## ADDED Requirements

### Requirement: Use bundled rules files
When the user chooses a bundled rules file, the web interface SHALL load it from its location in the repository, so that its `include` paths resolve exactly as on the command line, and SHALL produce the same results, report content, and cleaned data as the command-line tool run with that rules file on the same response data.

#### Scenario: Bundled modular configuration
- **WHEN** the user uploads a response file and chooses `config/ess2.json`
- **THEN** the overview metrics, detector table, scale table, and report download equal the results of `python detect_anomalies.py <response file> --rules config/ess2.json --report <path>`

#### Scenario: Bundled file needs no upload
- **WHEN** a bundled rules file is chosen and no rules file is uploaded
- **THEN** the run action is available once the response data file is uploaded
