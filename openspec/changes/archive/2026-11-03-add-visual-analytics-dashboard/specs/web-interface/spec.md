## ADDED Requirements

### Requirement: Show the quality score distribution
After a successful run, the web interface SHALL display a histogram of the quality scores of all scored respondents, with fixed bins of width 5 from 0 to 100 so that a bin edge falls on every multiple of 5. Respondents without a quality score SHALL NOT be counted in the histogram, and the interface SHALL state how many were left out. The histogram SHALL show a red dashed vertical line at the run's configured flag threshold (50 when the rules do not set one), labelled with the threshold value. Every non-empty bar SHALL show its count above it, so that a small bar stays readable next to a large one; empty bins SHALL show no count, and the value axis SHALL leave room above the tallest bar for its count. Above the histogram a horizontal choice "Y axis" SHALL offer `Log` and `Linear`, with `Log` selected by default; changing it SHALL NOT rerun the analysis or discard the results. On the log scale the value axis SHALL be titled "Respondents (log scale)", SHALL start below 1 so that a bin of a single respondent is a visible bar, SHALL label its ticks as plain integers (1, 10, 100, 1000), and empty bins SHALL get neither a bar nor a count; on the linear scale the axis SHALL be titled "Respondents" and start at 0. Bins whose upper edge is at or below the flag threshold, so that every score in them is suspicious, SHALL be drawn in red and all other bins in blue; a bin that straddles the threshold SHALL stay blue. A caption SHALL name the two colors and give the number of suspicious respondents and their share of the processed respondents with two decimals, for example `3 suspicious respondents (0.19%)`. The tick labels and axis titles of this and every other chart in the interface SHALL be shown in full, without being clipped and without overlapping each other.

#### Scenario: Log scale by default
- **WHEN** a run completes with 3 respondents in the 30–35 bin, 165 in 65–70, and 1446 in 95–100
- **THEN** the "Y axis" choice shows `Log`, the axis is logarithmic with ticks `1`, `10`, `100`, `1000` and a lower limit below 1, the bar of 3 is visible, and the 17 empty bins have no bar and no label

#### Scenario: Switching to the linear scale
- **WHEN** the user chooses `Linear`
- **THEN** the axis is linear from 0 with room above the tallest bar, titled "Respondents", and the metrics and tables of the same run stay displayed

#### Scenario: Suspicious bins are red
- **WHEN** the flag threshold is 50
- **THEN** the ten bins from 0–5 to 45–50 are red and the other ten blue; with a threshold of 52 the same ten bins are red and the 50–55 bin, which straddles the threshold, is blue

#### Scenario: Caption gives the suspicious share
- **WHEN** 3 of 1614 processed respondents are suspicious
- **THEN** the caption names the red and blue bars and states `3 suspicious respondents (0.19%)`

#### Scenario: Small bars carry their counts
- **WHEN** 1500 respondents score 100 and 4 score 33.33
- **THEN** the 30–35 bar is labelled `4` and the 95–100 bar `1500`, and no other bar has a label

#### Scenario: Axis labels are not clipped
- **WHEN** the histogram or the PCA map is shown
- **THEN** every tick label, including the minus sign of negative values, and both axis titles are fully visible and do not overlap

#### Scenario: Histogram counts match the scored respondents
- **WHEN** a run completes on `tests/fixtures/ess_mock.csv` with `config/scale_logic.json`
- **THEN** the histogram's total count equals the number of respondents with a quality score, and each respondent falls in the bin that contains its score

#### Scenario: Threshold line follows the configuration
- **WHEN** a run uses rules with `flag_threshold` 60
- **THEN** the red dashed line is drawn at 60 and labelled with 60; with no `flag_threshold` in the rules it is drawn at 50

#### Scenario: Unscored respondents are left out
- **WHEN** some respondents have no quality score
- **THEN** they are not in the histogram, and the interface states how many respondents were left out because they were not scored

#### Scenario: No scored respondent
- **WHEN** no respondent receives a quality score
- **THEN** the interface states that there are no quality scores to show instead of drawing an empty histogram

### Requirement: Show the Mahalanobis PCA map
After a successful run with at least one scale that runs the Mahalanobis detector, the web interface SHALL offer a choice of those scales (in rules order, the first one chosen by default) and SHALL display, for the chosen scale, a two-dimensional scatter plot of the first two principal components of that scale's item values. The plot SHALL contain exactly the respondents for whom a Mahalanobis distance was computed on that scale, using the same validated item values as the detector (missing codes and out-of-range values removed). The color SHALL describe the chosen scale: a respondent whose Mahalanobis distance on that scale exceeds the scale's threshold (the same scale-level flag that is counted in the "Mahalanobis flags (scale-level)" column of the scale-results table) SHALL be drawn in red, and every other respondent in grey. Independently of the color, respondents for whom the respondent-level Mahalanobis detector triggered (outliers on at least `mahalanobis_min_scales` scales) SHALL be drawn with a distinct marker shape and outline. The legend SHALL name both encodings, as "Outlier on this scale" for the red color and "Mahalanobis-flagged respondent (≥ m scales)" for the marker, with m replaced by the run's `mahalanobis_min_scales`. Because many respondents give identical answers, the points SHALL be drawn with a small, repeatable offset of at most 2% of each axis' standard deviation, so that identical answer patterns do not hide each other; the offset SHALL NOT change the projection, the distances, or the colors and markers. Hovering over a point SHALL show the respondent identifier (the `id_column` value, or the 1-based row number when no identifier column is configured), the respondent's exact component values without the offset, the respondent's Mahalanobis distance on the scale and the scale's threshold, whether the respondent is an outlier on this scale (yes/no), and whether the respondent is Mahalanobis-flagged (yes/no). The axis labels SHALL state the share of variance each component explains. A caption below the map SHALL explain that the two-dimensional projection shows the directions of largest variance while the Mahalanobis distance also measures directions of small variance, so an outlier on the scale can appear near the centre of the map, that the points are drawn with a small offset because of identical answers, and that the exact values are in the tooltip and the scale-results table. Changing the chosen scale SHALL NOT rerun the analysis or discard the results, and the projection SHALL be computed only for the scale being shown.

#### Scenario: Points are the detector's rows
- **WHEN** a run completes and a Mahalanobis scale is chosen
- **THEN** the plot has one point per respondent with a Mahalanobis distance on that scale, and no point for respondents missing any of its items

#### Scenario: Color shows outliers on the chosen scale
- **WHEN** a run completes and a Mahalanobis scale is chosen
- **THEN** exactly the points whose distance on that scale exceeds the scale's threshold are red, every other point is grey, and the number of red points equals the scale's "Mahalanobis flags (scale-level)" count in the scale-results table

#### Scenario: Marker shows respondent-level flags
- **WHEN** a run completes and a Mahalanobis scale is chosen
- **THEN** exactly the points of respondents for whom the respondent-level Mahalanobis detector triggered have the distinct marker shape and outline, and the legend names both "Outlier on this scale" and "Mahalanobis-flagged respondent (≥ m scales)" with the run's m

#### Scenario: Scale outlier that is not flagged, and flagged respondent that is not a scale outlier
- **WHEN** `mahalanobis_min_scales` is 3, one respondent exceeds the threshold only on the chosen scale, and another respondent is an outlier on three other scales but not on the chosen one
- **THEN** on the chosen scale's map the first respondent is red with the ordinary marker and the second is grey with the distinct marker

#### Scenario: Tooltip shows the identifier
- **WHEN** the rules configure `id_column` and the user hovers over a point
- **THEN** the tooltip shows that respondent's identifier value (without `id_column`, the 1-based row number), the distance on the scale, the scale's threshold, and yes/no for "outlier on this scale" and "Mahalanobis-flagged"

#### Scenario: Caption explains the projection
- **WHEN** a map is shown
- **THEN** a caption below it states that an outlier on the scale can lie near the centre of the two-dimensional projection, that the points are drawn with a small offset because of identical answers, and that the exact values are in the tooltip and the scale-results table

#### Scenario: Identical answers are drawn apart
- **WHEN** a map is shown twice for the same run and scale
- **THEN** every point is drawn at the same place both times, no point is further from its exact projection than 2% of the axis' standard deviation, the tooltip shows the exact projection, and the number of red points still equals the scale's "Mahalanobis flags (scale-level)" count

#### Scenario: Map not available
- **WHEN** the run has no Mahalanobis scale, or the chosen scale has fewer valid rows than its Mahalanobis minimum
- **THEN** the interface states why no map is shown instead of drawing an empty plot

### Requirement: Show a straightlining heatmap for a selected respondent
The detector-flagged respondents table SHALL allow the user to select one row. When the selected respondent was flagged for straightlining, the web interface SHALL display a heatmap with one row per scale on which the respondent was flagged for straightlining (in rules order) and one cell per item of that scale, holding the respondent's validated answer. Equal answer values SHALL have equal colors across the whole heatmap, every cell SHALL show its value as text, and hovering a cell SHALL show the item's column name. When the selected respondent was not flagged for straightlining, the interface SHALL say so instead of showing a heatmap. Selecting a row SHALL NOT rerun the analysis or discard the results. When the "Show suspicious respondents only" switch changes the visible rows, the selection SHALL refer to the row as displayed.

#### Scenario: Heatmap of a straightliner
- **WHEN** the user selects a respondent whose reasons include `Straightlining_Trust_Institutions`
- **THEN** a heatmap row for `Trust_Institutions` shows the respondent's values for each of its items, and all cells with the same value have the same color

#### Scenario: Several flagged scales
- **WHEN** a run on `tests/fixtures/ess_mock.csv` with `config/scale_logic.json` completes and the user selects respondent `1023`, flagged for straightlining on two scales
- **THEN** the heatmap has two rows, `Trust_Institutions` with 5 cells and `Satisfaction` with 4 cells, in this order

#### Scenario: Respondent without straightlining
- **WHEN** the user selects a respondent flagged only for a contradiction or a Mahalanobis outlier
- **THEN** no heatmap is shown, and the interface states that this respondent was not flagged for straightlining

#### Scenario: No selection
- **WHEN** no row is selected
- **THEN** no heatmap is shown, and the interface tells the user to select a flagged respondent to see the heatmap

### Requirement: Drill down into a flagged respondent
After a successful run with at least one detector-flagged respondent, the web interface SHALL display a "Respondent drill-down" section with a single-choice list of exactly the rows shown in the detector-flagged respondents table, in the same order, following the "Show suspicious respondents only" switch: with the switch off it offers every flagged respondent, with the switch on only the suspicious ones. Each choice SHALL be labelled with the respondent identifier (or the 1-based row number) and the quality score with two decimals, as `<identifier> (score 66.67)`, with `N/A` for an unscored respondent, and suspicious respondents SHALL carry the additional mark `suspicious`, as `<identifier> (score 33.33, suspicious)`. When the switch removes the chosen respondent from the list, the choice SHALL move to the first available respondent without an error. For the chosen respondent, the section SHALL show the quality score, the flag reasons grouped by detector (straightlining, contradiction, Mahalanobis), and a table of the respondent's logical contradictions with one row per condition of each triggered rule, giving the rule label, the column, the respondent's value, and the condition written as a full expression `<column> <operator> <value>` (for example `trstprt > 8`), so that no cell starts with an operator that the table could display as formatting; these rows SHALL be visually highlighted. When the respondent has no triggered contradiction rule, the section SHALL state that instead of showing the table. When the list would be empty, the section SHALL state that there is no respondent to inspect and show no list. Changing the chosen respondent SHALL NOT rerun the analysis or discard the results.

#### Scenario: Contradictions of the chosen respondent
- **WHEN** a run on `tests/fixtures/ess_mock.csv` with `config/scale_logic.json` completes and the user chooses respondent `1026`
- **THEN** the contradiction table has a row for `trstprt` and a row for `trstplt` under the label `Contradiction: trstprt>8 vs trstplt<2`, with the respondent's values and the conditions `trstprt > 8` and `trstplt < 2`, highlighted, and the reasons list `Mahalanobis_Trust_Institutions` under Mahalanobis

#### Scenario: Choices follow the flagged table with the switch off
- **WHEN** a run on `tests/fixtures/ess_mock.csv` with `config/scale_logic.json` completes and "Show suspicious respondents only" is off
- **THEN** the list offers `1026`, `1027`, `1032`, `1005`, `1021`, `1022`, `1023`, `1024`, `1033` in this order, the first three labelled with score 33.33 and `suspicious`, the others with score 66.67 and no mark

#### Scenario: Choices follow the flagged table with the switch on
- **WHEN** the same run is shown and the user turns on "Show suspicious respondents only"
- **THEN** the list offers exactly `1026`, `1027`, `1032`, the same rows as the displayed table

#### Scenario: Chosen respondent filtered out
- **WHEN** respondent `1023` is chosen and the user turns on "Show suspicious respondents only"
- **THEN** the choice moves to `1026`, its details are shown, and no error appears

#### Scenario: Every operator is shown as written
- **WHEN** the chosen respondent triggered a rule with the conditions `a > 8`, `b >= 7`, `c < 2`, `d <= 1.5`, and `e == 3`
- **THEN** the condition cells read exactly `a > 8`, `b >= 7`, `c < 2`, `d <= 1.5`, and `e == 3`, and no cell of the table starts with `>`

#### Scenario: Respondent without contradictions
- **WHEN** the chosen respondent has no triggered contradiction rule
- **THEN** the section states that the respondent has no logical contradictions and shows the other reasons

#### Scenario: Nothing to inspect
- **WHEN** the switch is on and no flagged respondent is suspicious
- **THEN** the section states that there is no respondent to inspect and shows no list

### Requirement: Visual analytics do not affect scoring or the command line
The visual elements SHALL be computed only from a finished run's results and SHALL NOT change the quality scores, flags, reasons, report content, cleaned data, or the results shown in the existing metrics and tables. The command-line tool SHALL NOT load the charting library or the visualization code, and its arguments, console output, exit codes, scored output, and report content SHALL stay unchanged. Visual elements SHALL write no file to disk.

#### Scenario: Command line does not load the visual libraries
- **WHEN** the command-line tool runs on `tests/fixtures/ess_mock.csv`
- **THEN** neither the charting library nor the visualization code has been imported in its process, and its output equals the output before the change

#### Scenario: Results unchanged by interaction
- **WHEN** the user changes the PCA scale, selects a flagged row, or chooses a respondent in the drill-down
- **THEN** the overview metrics, tables, report download, and cleaned-data download remain those of the same run

#### Scenario: Existing tests unchanged
- **WHEN** the pre-existing test files are run without modification after the change
- **THEN** all of them pass
