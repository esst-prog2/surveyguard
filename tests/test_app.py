import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pyreadstat
import pytest
from streamlit.testing.v1 import AppTest

from app import run_surveyguard
from surveyguard.errors import ConfigurationError, DataValidationError


FIXTURE_RULES = Path("tests/fixtures/rules.json")
FIXTURE_CSV = Path("tests/fixtures/survey.csv")
APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


@pytest.fixture
def isolated_tempdir(tmp_path, monkeypatch):
    workdir = tmp_path / "tmp"
    workdir.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(workdir))
    return workdir


def test_run_matches_cli_report_and_summary(tmp_path):
    report_path = tmp_path / "diagnostics.md"
    cli = subprocess.run(
        [
            sys.executable,
            "detect_anomalies.py",
            str(FIXTURE_CSV),
            "--rules",
            str(FIXTURE_RULES),
            "--output",
            str(tmp_path / "scored.csv"),
            "--report",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert cli.returncode == 0, cli.stdout + cli.stderr

    result = run_surveyguard("wave1.csv", FIXTURE_CSV.read_bytes(), FIXTURE_RULES.read_bytes())

    assert result.report_bytes == report_path.read_bytes()
    assert result.report_file_name == "wave1_diagnostics.md"
    assert f"Processed: {result.overview.processed}" in cli.stdout
    assert f"Suspicious: {result.overview.suspicious}" in cli.stdout
    assert f"Average quality score: {result.overview.average_score:.2f}" in cli.stdout
    assert result.detectors["Triggered"].tolist() == [1, 2, 0]
    assert result.flagged["Respondent"].tolist() == ["r1", "r2", "r3"]


def test_excel_and_spss_uploads_match_csv(tmp_path):
    source = pd.read_csv(FIXTURE_CSV)
    source["Q1"] = pd.to_numeric(source["Q1"], errors="coerce").fillna(3)
    csv_path = tmp_path / "survey.csv"
    xlsx_path = tmp_path / "survey.xlsx"
    sav_path = tmp_path / "survey.sav"
    source.to_csv(csv_path, index=False)
    source.to_excel(xlsx_path, index=False)
    pyreadstat.write_sav(
        source,
        sav_path,
        variable_value_labels={"Q1": {1: "One", 2: "Two", 3: "Three", 4: "Four"}},
    )
    rules = FIXTURE_RULES.read_bytes()

    expected = run_surveyguard(csv_path.name, csv_path.read_bytes(), rules)
    for path in (xlsx_path, sav_path):
        result = run_surveyguard(path.name.upper(), path.read_bytes(), rules)
        assert result.report_markdown == expected.report_markdown
        assert result.overview == expected.overview
        assert result.report_file_name == "SURVEY_diagnostics.md"


def test_invalid_rules_json_raises_user_facing_error(isolated_tempdir):
    with pytest.raises(ConfigurationError, match="Could not read rules JSON"):
        run_surveyguard("survey.csv", FIXTURE_CSV.read_bytes(), b"{not json")
    assert list(isolated_tempdir.iterdir()) == []


def test_missing_configured_column_raises_user_facing_error(isolated_tempdir):
    data = pd.read_csv(FIXTURE_CSV).drop(columns=["Q4"]).to_csv(index=False).encode("utf-8")
    with pytest.raises(DataValidationError, match="Missing configured question columns: Q4"):
        run_surveyguard("survey.csv", data, FIXTURE_RULES.read_bytes())
    assert list(isolated_tempdir.iterdir()) == []


def test_unsupported_extension_writes_no_input_file(isolated_tempdir):
    with pytest.raises(DataValidationError, match="Unsupported input extension: .txt"):
        run_surveyguard("survey.txt", FIXTURE_CSV.read_bytes(), FIXTURE_RULES.read_bytes())
    assert list(isolated_tempdir.iterdir()) == []


def test_successful_run_leaves_no_files(isolated_tempdir):
    run_surveyguard("survey.csv", FIXTURE_CSV.read_bytes(), FIXTURE_RULES.read_bytes())
    assert list(isolated_tempdir.iterdir()) == []


def test_app_renders_with_run_disabled_until_both_uploads():
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()

    assert not app.exception
    assert app.title[0].value == "SurveyGuard"
    assert app.button[0].label == "Run SurveyGuard"
    assert app.button[0].disabled
    assert app.info[0].value == "Upload the response data file and the rules file to run SurveyGuard."
    assert len(app.metric) == 0


def test_app_upload_run_download_and_reset_flow():
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    app.file_uploader[0].upload("survey.csv", FIXTURE_CSV.read_bytes(), "text/csv").run()
    assert app.button[0].disabled
    assert app.info[0].value == "Upload the rules file to run SurveyGuard."
    app.file_uploader[1].upload("rules.json", FIXTURE_RULES.read_bytes(), "application/json").run()
    assert not app.button[0].disabled

    app.button[0].click().run()

    assert not app.exception
    assert len(app.error) == 0
    assert [metric.label for metric in app.metric] == [
        "Processed respondents",
        "Suspicious respondents",
        "Average quality score",
    ]
    assert [metric.value for metric in app.metric] == ["7", "0", "85.71"]
    assert len(app.dataframe) == 2
    assert app.dataframe[0].value["Triggered"].tolist() == [1, 2, 0]
    assert app.dataframe[1].value["Respondent"].tolist() == ["r1", "r2", "r3"]
    assert app.download_button[0].label == "Download diagnostic report"

    app.download_button[0].click().run()
    assert [metric.value for metric in app.metric] == ["7", "0", "85.71"]

    app.file_uploader[1].upload("rules.json", b"{not json", "application/json").run()
    assert len(app.metric) == 0
    app.button[0].click().run()
    assert app.error[0].value.startswith("Error: Could not read rules JSON")
    assert len(app.metric) == 0
    assert len(app.dataframe) == 0
