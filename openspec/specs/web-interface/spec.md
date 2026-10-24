# web-interface Specification

## Purpose

Defines the observable behavior of SurveyGuard's browser-based interface, which lets users upload a response file and a rules file, run the existing detection pipeline, inspect the results interactively, and download the diagnostic report without using the command line.

## Requirements

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

### Requirement: Process uploads with the existing pipeline
When the user triggers the run, the web interface SHALL apply the same rules validation, input loading, scoring, and report generation as the command-line tool, so that for identical inputs the results are identical. SPSS inputs SHALL be read with raw numeric codes, as in the command-line tool. Uploaded files SHALL NOT be stored beyond the duration of the run, and no file SHALL be written to the repository or next to the original input.

#### Scenario: Same results as the command line
- **WHEN** the same response file and rules file are processed once through the web interface and once with the command-line tool using `--report`
- **THEN** the processed, suspicious, and average-score values match the command-line summary, and the downloadable report is byte-for-byte identical to the command-line report file

#### Scenario: Excel and SPSS uploads
- **WHEN** a valid `.xlsx` or `.sav` response file is uploaded together with matching rules
- **THEN** the run succeeds and produces the same results as the equivalent `.csv` input

#### Scenario: No persistent files
- **WHEN** a run completes or fails
- **THEN** no scored dataset, report, or copy of the uploaded files remains on disk as a result of the run

### Requirement: Display overview metrics
After a successful run, the web interface SHALL display the processed respondent count, the suspicious respondent count, and the average quality score as headline metrics. The average quality score SHALL be shown with two decimals, computed over scored respondents only, and SHALL be shown as `N/A` when no respondent could be scored.

#### Scenario: Overview after a run
- **WHEN** a run completes on an input with a known number of processed and suspicious respondents
- **THEN** the three metrics show exactly those counts and the same average quality score as the diagnostic report

#### Scenario: No scored respondents
- **WHEN** no respondent receives a quality score
- **THEN** the average quality score metric shows `N/A`

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

### Requirement: Download the diagnostic report
After a successful run, the web interface SHALL offer a download of the Markdown diagnostic report for that run. The downloaded file SHALL have the same content as the report the command-line tool writes with `--report` and SHALL be named after the uploaded response file's stem with the suffix `_diagnostics.md`. Downloading SHALL NOT discard the displayed results.

#### Scenario: Report download
- **WHEN** the user downloads the report after a run on `wave1.xlsx`
- **THEN** the browser receives `wave1_diagnostics.md` encoded as UTF-8 with the full report content

#### Scenario: Results stay visible after download
- **WHEN** the user clicks the download button
- **THEN** the metrics and tables of the same run remain displayed

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

### Requirement: Command-line behavior is preserved
Adding the web interface SHALL NOT change the command-line tool's arguments, console output, exit codes, scored output, or report content.

#### Scenario: Existing test suite unchanged
- **WHEN** the pre-existing unit and command-line tests are run without modification after the change
- **THEN** all of them pass

### Requirement: Show run feedback
While a run is in progress, the web interface SHALL show a "Processing data..." progress indicator. After a successful run it SHALL show an "Analysis complete!" success message in the main area. When the run fails with an expected error, it SHALL show only the error message and no success message.

#### Scenario: Successful run feedback
- **WHEN** the user triggers a run that succeeds
- **THEN** the "Analysis complete!" message is shown together with the results

#### Scenario: Failed run feedback
- **WHEN** the user triggers a run that fails because of an invalid rules or response file
- **THEN** an `Error:` message is shown and no "Analysis complete!" message appears

### Requirement: Visualize detector percentages
After a successful run, the web interface SHALL display a bar chart with one bar per detector, in the same order as the detector-results table. Each bar's height SHALL be the detector's percentage of processed respondents, and the value axis SHALL be labelled as a percentage.

#### Scenario: Chart matches the detector table
- **WHEN** a run completes
- **THEN** the chart shows the straightlining, contradiction, and Mahalanobis bars in that order, with heights equal to the `Percentage` values of the detector-results table

### Requirement: Download cleaned data
After a successful run, the web interface SHALL offer, next to the report download, a download of the uploaded response data with every suspicious respondent (quality score below the configured flag threshold) removed. The file SHALL be CSV regardless of the uploaded format, SHALL be named after the uploaded response file's stem with the suffix `_cleaned.csv`, SHALL contain exactly the uploaded file's columns in their original order with values as loaded (raw numeric codes for SPSS inputs) and no scoring columns, and SHALL keep the remaining rows in input order. Respondents without a quality score are not suspicious and SHALL be kept. The interface SHALL state how many respondents were removed and how many were kept.

#### Scenario: Suspicious respondents removed
- **WHEN** a run on an input with a known set of suspicious respondents completes and the user downloads the cleaned data
- **THEN** the CSV contains every other row in input order, the same columns as the input, and none of the suspicious respondents

#### Scenario: Nothing to remove
- **WHEN** no respondent is suspicious
- **THEN** the cleaned data contains all input rows, and the interface states that 0 respondents were removed

#### Scenario: Non-CSV input
- **WHEN** the uploaded response file is `.xlsx` or `.sav`
- **THEN** the cleaned download is named `<stem>_cleaned.csv` and contains the same rows and values as for the equivalent `.csv` input

#### Scenario: No cleaned file on disk
- **WHEN** a run completes or the cleaned data is downloaded
- **THEN** no cleaned or scored data file is written to disk by the interface

### Requirement: Use bundled rules files
When the user chooses a bundled rules file, the web interface SHALL load it from its location in the repository, so that its `include` paths resolve exactly as on the command line, and SHALL produce the same results, report content, and cleaned data as the command-line tool run with that rules file on the same response data.

#### Scenario: Bundled modular configuration
- **WHEN** the user uploads a response file and chooses `config/ess2.json`
- **THEN** the overview metrics, detector table, scale table, and report download equal the results of `python detect_anomalies.py <response file> --rules config/ess2.json --report <path>`

#### Scenario: Bundled file needs no upload
- **WHEN** a bundled rules file is chosen and no rules file is uploaded
- **THEN** the run action is available once the response data file is uploaded
