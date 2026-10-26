## MODIFIED Requirements

### Requirement: Use bundled rules files
When the user chooses a bundled rules file, the web interface SHALL load it from its location in the repository, so that its `include` paths resolve exactly as on the command line, and SHALL produce the same results, report content, and cleaned data as the command-line tool run with that rules file on the same response data. The bundled choices SHALL be every top-level `config/*.json` file, found without a hard-coded list, so that a new top-level rules file is offered without changing the interface. The choices SHALL be in natural order: the digit runs in file names compare as numbers, and the other parts compare case-insensitively.

#### Scenario: Bundled modular configuration
- **WHEN** the user uploads a response file and chooses `config/ess2.json`
- **THEN** the overview metrics, detector table, scale table, and report download equal the results of `python detect_anomalies.py <response file> --rules config/ess2.json --report <path>`

#### Scenario: Bundled file needs no upload
- **WHEN** a bundled rules file is chosen and no rules file is uploaded
- **THEN** the run action is available once the response data file is uploaded

#### Scenario: Every ESS round is offered in natural order
- **WHEN** the user chooses the bundled rules source
- **THEN** the choices are exactly `config/ess1.json`, `config/ess2.json`, … `config/ess11.json`, `config/scale_logic.json`, `config/spike_logic.json` in this order, and no module file from `config/ess/` is offered
