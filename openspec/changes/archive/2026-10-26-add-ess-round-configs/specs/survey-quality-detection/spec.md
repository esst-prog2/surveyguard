## ADDED Requirements

### Requirement: Provide modular ESS configurations for every round
The repository SHALL ship a root rules file `config/essN.json` for every ESS round N from 1 to 11, and every root file SHALL set `essround` to its round N. `config/ess/core.json` and every `config/ess/r2_*.json` file SHALL remain byte-identical to their state before this change, and `config/ess2.json` SHALL change only by its `essround` key. Every other root file SHALL include `config/ess/common_core.json`, then `config/ess/rN_core.json`, then the round's rotating module files `config/ess/rN_<topic>.json`, and SHALL set `id_column` `idno`, `flag_threshold` `50`, `mahalanobis_min_scales` `3`, and the default detector weights. `common_core.json` SHALL contain only scales whose column list is present in all 11 rounds and only variables present in all 11 rounds. Scales and variables in `common_core.json` and `rN_core.json` SHALL have `module` `core` and `required` `true`; those in rotating files SHALL have `module` `rotating` and `required` `false`. Every scale SHALL contain at least three items; a core scale that has fewer than three items in a round SHALL be left out of that round, and its items SHALL be declared as variables only when a contradiction rule uses them. Every scale SHALL set `mahalanobis_alpha` `0.01`, `min_items_straightlining` `5`, and `mahalanobis_min_rows_per_item` `10`. A scale whose real straightlining rate on its round's data exceeds 5% SHALL list only the `mahalanobis_outlier` detector. Every column that a round's configuration names SHALL exist in that round's SPSS file. Binary and categorical variables, counts, years, country-specific variables, and behaviour or event-frequency blocks SHALL NOT be scales; those that rules need SHALL be declared as variables.

#### Scenario: Every round has a bundled configuration
- **WHEN** the `config/` folder is listed after the change
- **THEN** it contains `ess1.json` through `ess11.json`, each loads without a configuration error, and each has `essround` equal to the number in its file name

#### Scenario: ESS2 changes only by its round key
- **WHEN** the change is compared with the previous `main`
- **THEN** `config/ess/core.json` and the three `config/ess/r2_*.json` files have no diff, the only diff in `config/ess2.json` is the added `essround` `2`, and the ESS2 tests keep their expected scoring results

#### Scenario: Short core scale left out
- **WHEN** a round has only `gincdif` and `freehms` of the `Policy_Attitudes` items
- **THEN** that round's configuration has no `Policy_Attitudes` scale, and neither column is declared unless a contradiction rule uses it

#### Scenario: Core-only data for a round
- **WHEN** the CLI is run with `config/essN.json` on synthetic data that contains `essround` N and every column of `common_core.json` and `rN_core.json` and no rotating column
- **THEN** the run succeeds and the summary lists every rotating scale of that round under `Skipped scales:`

#### Scenario: Real round file runs
- **WHEN** the CLI is run manually, outside the repository, on a round's real SPSS file with its `config/essN.json`
- **THEN** the run succeeds with no structural error and no skipped core scale

### Requirement: Check the ESS round of the input data
A root rules file MAY define `essround`, a positive integer. When it is defined, loading the input SHALL fail with a clear structural error, before any scoring and through the same error path as a missing configured column, if the input has no `essround` column, if the column has no non-missing value, or if any non-missing value differs from the configured round; a mismatch error SHALL state the expected round and every distinct round found, for example `Rules file expects ESS round 3, but the data contains essround 4`. Missing values in the column SHALL be ignored. When `essround` is not defined, the input SHALL NOT be checked for a round. A value that is not a positive integer (for example `0`, `"3"`, or `2.5`) SHALL be a configuration error, and `essround` in an included file SHALL be a configuration error that names the file. The command-line tool and the web interface SHALL report these errors through their existing error handling.

#### Scenario: Matching round
- **WHEN** the rules set `essround` `3` and every non-missing `essround` value in the input is `3`
- **THEN** the run succeeds with the same results as without the key

#### Scenario: Different round
- **WHEN** the rules set `essround` `3` and the input's `essround` values are `4`
- **THEN** the command exits with the structural error `Rules file expects ESS round 3, but the data contains essround 4` and writes no scored output

#### Scenario: Missing round column
- **WHEN** the rules set `essround` `3` and the input has no `essround` column
- **THEN** the command exits with a structural error stating that the rules file expects ESS round 3 and the data has no `essround` column

#### Scenario: Empty round column
- **WHEN** the rules set `essround` `3` and every value of the input's `essround` column is missing
- **THEN** the command exits with a structural error stating that the data contains no `essround` value

#### Scenario: No round key
- **WHEN** the rules do not define `essround` and the input has an `essround` column with the value `4`, or no such column
- **THEN** the run behaves exactly as before the change

#### Scenario: Round key in an included file
- **WHEN** an included file defines `essround`
- **THEN** rules loading fails with a configuration error naming `essround` and the included file

#### Scenario: Invalid round value
- **WHEN** the root file sets `essround` to `0`, `"3"`, or `2.5`
- **THEN** rules loading fails with a configuration error stating that `essround` must be a positive integer

#### Scenario: Wrong round in the web interface
- **WHEN** the user uploads a file whose `essround` is `4` and chooses the bundled `config/ess3.json`
- **THEN** the web interface shows the same round error as the command-line tool and no results

### Requirement: Derive ESS missing codes and ranges from value labels
For the rounds whose SPSS files declare no user-missing values, each scale's and variable's `missing_codes` SHALL be the union, over its columns, of the codes whose value label is `Refusal`, `Don't know`, `No answer`, `Not applicable`, or `Not available`. `valid_min` and `valid_max` SHALL be the smallest and largest substantive code of its columns. A scale SHALL contain only columns with the same substantive range.

#### Scenario: Eleven-point item
- **WHEN** an item's value labels are `0` … `10` plus `77` `Refusal`, `88` `Don't know`, and `99` `No answer`
- **THEN** its scale has `valid_min` `0`, `valid_max` `10`, and `missing_codes` `77`, `88`, and `99`

### Requirement: Generate round-specific contradiction rules
Every round's configuration SHALL contain explicit contradiction rules from the ESS2 families, each emitted only when all of its columns exist in that round: political trust (`trstplt` `>` `8` with `trstprl` `<` `2`; `trstprt` `>` `8` with `trstplt` `<` `2`), satisfaction (`stfgov` `>` `8` with `stfdem` `<` `2`), household size and composition (living with a partner versus a one-person household or the interviewer code, a one-person household with a second person's gender, no partner with `rshipa2`–`rshipa6` `==` `1`, no children at home with `rshipa2`–`rshipa6` `==` `2`), and age against year of birth. For a round with fieldwork year Y, the largest value of `agea + yrbrn` in its data, the age rules SHALL be `agea` `<=` `30` with `yrbrn` `<=` Y−36 and `agea` `>=` `60` with `yrbrn` `>=` Y−54. A rule SHALL be placed in the file that defines all of its columns; a rule whose columns are defined in different files, and the age rules, SHALL be placed in the root file.

#### Scenario: Rule columns missing in a round
- **WHEN** a round has no `trstprt` column
- **THEN** its configuration contains no rule that references `trstprt`

#### Scenario: Age rules reproduce ESS2
- **WHEN** the fieldwork year formula is applied to ESS2 (Y = 2005)
- **THEN** it yields the existing thresholds `1969` and `1951`

### Requirement: Keep real SPSS files out of version control
The repository's `.gitignore` SHALL ignore the `ess_sav_files/` folder and every `*.sav` file, and no `.sav` file SHALL be tracked.

#### Scenario: Real files are ignored
- **WHEN** `git status --ignored` is run with the real round files in `ess_sav_files/`
- **THEN** they are listed as ignored, and `git ls-files` lists no `.sav` file

### Requirement: Validate every bundled rules file
The project SHALL include a deterministic test that finds every `config/**/*.json` file without a hard-coded list. It SHALL check that every top-level file loads with the rules loader; that every `include` entry is a relative POSIX path to an existing file inside `config/`; that every scale name matches `^[A-Za-z0-9_]+$`; that every file in a subfolder contains only `include`, `scales`, `variables`, and `contradictions` and is included by at least one top-level file; that every `config/essN.json` sets `essround` N; and that every `config/essN.json` succeeds on synthetic data with all of its columns and an `essround` column of N. The test SHALL use no real survey data.

#### Scenario: A broken bundled file is caught
- **WHEN** a bundled file has an include path to a missing file, a scale name with a space, or a module that no root file includes
- **THEN** the test fails and names the file

#### Scenario: New files are picked up automatically
- **WHEN** a new valid `config/ess12.json` with its modules is added
- **THEN** the test covers it without being edited

## MODIFIED Requirements

### Requirement: Compose rules from included files
A rules file MAY define an `include` list of rules-file paths, each resolved relative to the directory of the file that lists it. The system SHALL load included files depth-first, in list order, before the including file's own entries, and SHALL merge their `scales`, `variables`, and `contradictions` in that order. An included file SHALL contain only `include`, `scales`, `variables`, and `contradictions`; `weights`, `flag_threshold`, `mahalanobis_min_scales`, `id_column`, and `essround` SHALL be accepted only in the root file. All validation rules SHALL apply to the merged configuration. The system SHALL reject, with a clear configuration error, an include cycle (naming the files of the cycle in order), a file that is included more than once, an included file that cannot be read, a scale name or variable defined in two files, and a column that belongs to scales or variables of two files; each error about a conflict SHALL name both files.

#### Scenario: Include chain
- **WHEN** `root.json` includes `modules/a.json`, which includes `b.json` in the same `modules` folder, and each file defines one scale
- **THEN** the merged rules contain the scales of `b.json`, `modules/a.json`, and `root.json` in that order, and the run produces the same result as a single file with those three scales

#### Scenario: Circular include
- **WHEN** `a.json` includes `b.json` and `b.json` includes `a.json`
- **THEN** rules loading fails with a configuration error that names `a.json` and `b.json` and states that the include is circular

#### Scenario: Scale name defined in two files
- **WHEN** two included files both define a scale named `Social_Trust`
- **THEN** rules loading fails with a configuration error naming `Social_Trust` and both files

#### Scenario: Column used in two files
- **WHEN** `core.json` lists `trstprl` in `Trust_Institutions` and an included `extra.json` lists `trstprl` in another scale
- **THEN** rules loading fails with a configuration error naming `trstprl`, both scales, and both files

#### Scenario: Root-only setting in an included file
- **WHEN** an included file defines `flag_threshold`
- **THEN** rules loading fails with a configuration error naming `flag_threshold` and the included file

#### Scenario: Minimum Mahalanobis scales in an included file
- **WHEN** an included file defines `mahalanobis_min_scales`
- **THEN** rules loading fails with a configuration error naming `mahalanobis_min_scales` and the included file

#### Scenario: Invalid minimum Mahalanobis scales
- **WHEN** the root file sets `mahalanobis_min_scales` to `0`, `2.5`, or `"3"`
- **THEN** rules loading fails with a configuration error stating that `mahalanobis_min_scales` must be a positive integer

### Requirement: Provide modular ESS round 2 configurations
The repository SHALL ship `config/ess2.json`, which includes `config/ess/core.json`, `config/ess/r2_health.json`, `config/ess/r2_econ_morality.json`, and `config/ess/r2_family_work.json`, sets `id_column` `idno`, `essround` `2`, `flag_threshold` `50`, and `mahalanobis_min_scales` `3`, and defines the round-specific socio-demographic contradiction rules. Scales in `core.json` SHALL have `module` `core` and `required` `true`; scales and variables in the three `r2_*` files SHALL have `module` `rotating` and `required` `false`. Every ESS scale SHALL set `mahalanobis_alpha` `0.01`, `min_items_straightlining` `5`, and `mahalanobis_min_rows_per_item` `10`, and SHALL list as `missing_codes` the codes that the ESS round 2 SPSS metadata declares as user-missing for its items. Binary and categorical variables, counts, years, and behaviour or event-frequency blocks SHALL NOT be scales; those that rules need SHALL be declared as variables. The synthetic fixture `tests/fixtures/ess2_mock.csv` SHALL contain an `essround` column with the value `2` in every row. The existing `config/scale_logic.json` SHALL remain unchanged and keep working.

#### Scenario: Core-only data
- **WHEN** the CLI is run with `config/ess2.json` on synthetic data that contains `essround` `2`, every core column, and no rotating-module column
- **THEN** the run succeeds and the summary lists every rotating scale under `Skipped scales:`

#### Scenario: Real ESS data stays out of the repository
- **WHEN** the repository contents are listed after the change
- **THEN** no real ESS respondent data is present; the ESS round 2 file is used only for manual metadata checks and a manual smoke run outside the repository

### Requirement: Deterministically verify fast scoring
The project SHALL include deterministic tests with synthetic or public fixture data that compare the column-wise scoring with the row-by-row reference and check that loaded inputs carry no metadata. These tests SHALL NOT assert wall-clock time limits. The full test suite SHALL contain at least 162 tests, and the expected scoring results of the tests that existed before the column-wise scoring change SHALL NOT be changed.

#### Scenario: Fast scoring is tested without timing assertions
- **WHEN** the full test suite is run
- **THEN** it passes with at least 162 tests, includes the equivalence and metadata tests, and contains no assertion on elapsed time
