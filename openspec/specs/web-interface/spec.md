# web-interface Specification

## Purpose

Defines the observable behavior of SurveyGuard's browser-based interface, which lets users upload a response file and a rules file, run the existing detection pipeline, inspect the results interactively, and download the diagnostic report without using the command line.

## Requirements

### Requirement: Accept uploaded inputs
The web interface SHALL provide one upload control for the response data file that accepts `.csv`, `.xlsx`, and `.sav` files and one upload control for the rules file that accepts `.json` files. The run action SHALL be unavailable until both files have been provided.

#### Scenario: Both files are required
- **WHEN** the interface is opened and only one of the two files, or neither, has been uploaded
- **THEN** the "Run SurveyGuard" action cannot be triggered and the interface tells the user which upload is still missing

#### Scenario: Run becomes available
- **WHEN** a supported response file and a `.json` rules file have both been uploaded
- **THEN** the "Run SurveyGuard" action can be triggered

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
After a successful run, the web interface SHALL display an interactive detector-results table with one row per detector (straightlining, contradiction, Mahalanobis) showing its trigger count and its percentage of processed respondents. It SHALL also display an interactive table of detector-flagged respondents, meaning respondents who are suspicious or have at least one detector reason, showing the respondent identifier (or the 1-based row number when no identifier column is configured), the quality score, whether the respondent is suspicious, and the flag reasons, in the same order as the diagnostic report.

#### Scenario: Detector table matches the report
- **WHEN** a run completes
- **THEN** each detector's count and percentage in the table equal the values in the report's detector table

#### Scenario: Flagged respondents table
- **WHEN** one or more respondents are suspicious or have detector reasons
- **THEN** the flagged table lists exactly those respondents, ordered by ascending quality score with input order breaking ties and unscored respondents last, with their exact reason text

#### Scenario: Nothing flagged
- **WHEN** no respondent is suspicious or detector-flagged
- **THEN** the interface states that no respondents were flagged instead of showing an empty table

### Requirement: Download the diagnostic report
After a successful run, the web interface SHALL offer a download of the Markdown diagnostic report for that run. The downloaded file SHALL have the same content as the report the command-line tool writes with `--report` and SHALL be named after the uploaded response file's stem with the suffix `_diagnostics.md`. Downloading SHALL NOT discard the displayed results.

#### Scenario: Report download
- **WHEN** the user downloads the report after a run on `wave1.xlsx`
- **THEN** the browser receives `wave1_diagnostics.md` encoded as UTF-8 with the full report content

#### Scenario: Results stay visible after download
- **WHEN** the user clicks the download button
- **THEN** the metrics and tables of the same run remain displayed

### Requirement: Report expected failures without crashing
When the rules file or the response file is invalid (unreadable JSON, invalid rule definitions, unreadable data, or missing configured columns), the web interface SHALL show a single error message beginning with `Error:` that contains the same explanation the command-line tool prints, SHALL NOT show a traceback for these failures, and SHALL NOT show results from a previous run as if they belonged to the new inputs.

#### Scenario: Invalid rules file
- **WHEN** the uploaded rules file is not valid JSON
- **THEN** the interface shows an `Error:` message explaining that the rules JSON could not be read and shows no metrics or tables

#### Scenario: Missing configured columns
- **WHEN** the response file lacks a question column named in the rules
- **THEN** the interface shows an `Error:` message naming the missing columns and shows no metrics or tables

#### Scenario: Inputs changed after a run
- **WHEN** the user replaces either uploaded file after a successful run
- **THEN** the previous run's results are no longer displayed until the run action is triggered again

### Requirement: Command-line behavior is preserved
Adding the web interface SHALL NOT change the command-line tool's arguments, console output, exit codes, scored output, or report content.

#### Scenario: Existing test suite unchanged
- **WHEN** the pre-existing unit and command-line tests are run without modification after the change
- **THEN** all of them pass
