## MODIFIED Requirements

### Requirement: Accept uploaded inputs
The web interface SHALL provide, in a sidebar that is separate from the main results area, one upload control for the response data file that accepts `.csv`, `.xlsx`, and `.sav` files, one upload control for the rules file that accepts `.json` files, and the "Run SurveyGuard" action. The run action SHALL be unavailable until both files have been provided. The main area SHALL be reserved for guidance, run feedback, and results.

#### Scenario: Both files are required
- **WHEN** the interface is opened and only one of the two files, or neither, has been uploaded
- **THEN** the "Run SurveyGuard" action cannot be triggered and the sidebar tells the user which upload is still missing

#### Scenario: Run becomes available
- **WHEN** a supported response file and a `.json` rules file have both been uploaded
- **THEN** the "Run SurveyGuard" action can be triggered

#### Scenario: Controls live in the sidebar
- **WHEN** the interface is opened
- **THEN** both upload controls and the "Run SurveyGuard" action are in the sidebar, and the main area shows a hint to upload the files in the sidebar instead of results

### Requirement: Display interactive result tables
After a successful run, the web interface SHALL display an interactive detector-results table with one row per detector (straightlining, contradiction, Mahalanobis) showing its trigger count and its percentage of processed respondents. It SHALL also display an interactive table of detector-flagged respondents, meaning respondents who are suspicious or have at least one detector reason, showing the respondent identifier (or the 1-based row number when no identifier column is configured), the quality score, whether the respondent is suspicious, and the flag reasons, in the same order as the diagnostic report. A "Show suspicious respondents only" switch above the flagged table SHALL be off by default; when it is on, the table SHALL show only the rows whose `Suspicious` value is true, in the same relative order, and the full table SHALL return when it is switched off. Changing the switch SHALL NOT rerun the analysis or discard the results.

#### Scenario: Detector table matches the report
- **WHEN** a run completes
- **THEN** each detector's count and percentage in the table equal the values in the report's detector table

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

## ADDED Requirements

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
