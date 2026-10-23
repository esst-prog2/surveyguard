import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pyreadstat
import pytest
from streamlit.dataframe_util import convert_arrow_bytes_to_pandas_df
from streamlit.testing.v1 import AppTest

from app import run_surveyguard
from surveyguard.errors import ConfigurationError, DataValidationError


FIXTURE_RULES = Path("config/scale_logic.json")
FIXTURE_CSV = Path("tests/fixtures/ess_mock.csv")
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
    assert result.detectors["Triggered"].tolist() == [4, 4, 4]
    assert result.flagged["Respondent"].tolist() == FLAGGED_IDS


def test_excel_and_spss_uploads_match_csv(tmp_path):
    source = pd.read_csv(FIXTURE_CSV)
    source["stflife"] = pd.to_numeric(source["stflife"], errors="coerce").fillna(6)
    csv_path = tmp_path / "survey.csv"
    xlsx_path = tmp_path / "survey.xlsx"
    sav_path = tmp_path / "survey.sav"
    source.to_csv(csv_path, index=False)
    source.to_excel(xlsx_path, index=False)
    pyreadstat.write_sav(
        source,
        sav_path,
        variable_value_labels={"trstprl": {0: "No trust at all", 10: "Complete trust"}},
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
    data = pd.read_csv(FIXTURE_CSV).drop(columns=["stfdem"]).to_csv(index=False).encode("utf-8")
    with pytest.raises(DataValidationError, match="Missing configured question columns: stfdem"):
        run_surveyguard("survey.csv", data, FIXTURE_RULES.read_bytes())
    assert list(isolated_tempdir.iterdir()) == []


def test_unsupported_extension_writes_no_input_file(isolated_tempdir):
    with pytest.raises(DataValidationError, match="Unsupported input extension: .txt"):
        run_surveyguard("survey.txt", FIXTURE_CSV.read_bytes(), FIXTURE_RULES.read_bytes())
    assert list(isolated_tempdir.iterdir()) == []


def test_successful_run_leaves_no_files(isolated_tempdir):
    run_surveyguard("survey.csv", FIXTURE_CSV.read_bytes(), FIXTURE_RULES.read_bytes())
    assert list(isolated_tempdir.iterdir()) == []


SUSPICIOUS_IDS = [1026, 1027, 1032]
FLAGGED_IDS = [1026, 1027, 1032, 1005, 1021, 1022, 1023, 1024, 1033]


def _rules_without_suspicious() -> bytes:
    # A score cannot fall below 0, so flag_threshold 0 marks nobody as suspicious.
    rules = json.loads(FIXTURE_RULES.read_text(encoding="utf-8"))
    rules["flag_threshold"] = 0
    return json.dumps(rules).encode("utf-8")


def _without_suspicious(source: pd.DataFrame) -> pd.DataFrame:
    return source.loc[~source["idno"].isin(SUSPICIOUS_IDS)].reset_index(drop=True)


def _read_cleaned(result) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(result.cleaned_csv))


def test_cleaned_data_removes_suspicious_respondents(isolated_tempdir):
    result = run_surveyguard("wave1.csv", FIXTURE_CSV.read_bytes(), FIXTURE_RULES.read_bytes())

    assert result.overview.suspicious == 3
    assert (result.removed_count, result.kept_count) == (3, 30)
    assert result.cleaned_file_name == "wave1_cleaned.csv"
    pd.testing.assert_frame_equal(_read_cleaned(result), _without_suspicious(pd.read_csv(FIXTURE_CSV)))
    assert list(isolated_tempdir.iterdir()) == []


def test_cleaned_data_keeps_all_rows_when_nothing_is_suspicious():
    result = run_surveyguard("ess.csv", FIXTURE_CSV.read_bytes(), _rules_without_suspicious())

    assert (result.removed_count, result.kept_count) == (0, 33)
    pd.testing.assert_frame_equal(_read_cleaned(result), pd.read_csv(FIXTURE_CSV))


def test_cleaned_data_keeps_unscored_respondents():
    source = pd.read_csv(FIXTURE_CSV)
    unscored = pd.DataFrame([[2001, "HU"] + [99] * 9], columns=source.columns)
    data = pd.concat([source, unscored], ignore_index=True).to_csv(index=False).encode("utf-8")

    result = run_surveyguard("ess.csv", data, FIXTURE_RULES.read_bytes())

    assert result.overview.not_scored == 1
    assert (result.removed_count, result.kept_count) == (3, 31)
    expected = [idno for idno in source["idno"] if idno not in SUSPICIOUS_IDS] + [2001]
    assert _read_cleaned(result)["idno"].tolist() == expected


def test_cleaned_data_from_excel_and_spss_matches_csv(tmp_path):
    source = pd.read_csv(FIXTURE_CSV)
    source["stflife"] = pd.to_numeric(source["stflife"], errors="coerce").fillna(6)
    csv_path = tmp_path / "ess.csv"
    xlsx_path = tmp_path / "ess.xlsx"
    sav_path = tmp_path / "ess.sav"
    source.to_csv(csv_path, index=False)
    source.to_excel(xlsx_path, index=False)
    pyreadstat.write_sav(source, sav_path)
    rules = FIXTURE_RULES.read_bytes()

    expected = run_surveyguard(csv_path.name, csv_path.read_bytes(), rules)
    assert expected.removed_count == 3
    for path in (xlsx_path, sav_path):
        result = run_surveyguard(path.name, path.read_bytes(), rules)
        assert result.cleaned_file_name == "ess_cleaned.csv"
        assert (result.removed_count, result.kept_count) == (3, 30)
        # SPSS codes load as floats (3 -> 3.0), so compare values, not dtypes.
        pd.testing.assert_frame_equal(_read_cleaned(result), _read_cleaned(expected), check_dtype=False)


MAIN_HINT = "Upload the response data and rules files in the sidebar, then click Run SurveyGuard."


def _run_app(data: bytes, data_name: str = "survey.csv", rules: bytes | None = None) -> AppTest:
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    app.sidebar.file_uploader[0].upload(data_name, data, "text/csv").run()
    rules = FIXTURE_RULES.read_bytes() if rules is None else rules
    app.sidebar.file_uploader[1].upload("rules.json", rules, "application/json").run()
    app.sidebar.button[0].click().run()
    assert not app.exception
    return app


def test_app_renders_with_run_disabled_until_both_uploads():
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()

    assert not app.exception
    assert app.title[0].value == "SurveyGuard"
    assert app.sidebar.header[0].value == "Inputs"
    assert len(app.sidebar.file_uploader) == 2
    assert len(app.main.file_uploader) == 0
    assert len(app.main.button) == 0
    assert app.sidebar.button[0].label == "Run SurveyGuard"
    assert app.sidebar.button[0].disabled
    assert app.sidebar.info[0].value == "Upload the response data file and the rules file to run SurveyGuard."
    assert [info.value for info in app.main.info] == [MAIN_HINT]
    assert len(app.metric) == 0


def test_app_upload_run_download_and_reset_flow():
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    app.sidebar.file_uploader[0].upload("survey.csv", FIXTURE_CSV.read_bytes(), "text/csv").run()
    assert app.sidebar.button[0].disabled
    assert app.sidebar.info[0].value == "Upload the rules file to run SurveyGuard."
    app.sidebar.file_uploader[1].upload("rules.json", FIXTURE_RULES.read_bytes(), "application/json").run()
    assert not app.sidebar.button[0].disabled
    assert len(app.sidebar.info) == 0

    app.sidebar.button[0].click().run()

    assert not app.exception
    assert len(app.error) == 0
    assert [message.value for message in app.success] == ["Analysis complete!"]
    assert MAIN_HINT not in [info.value for info in app.main.info]
    assert [metric.label for metric in app.metric] == [
        "Processed respondents",
        "Suspicious respondents",
        "Average quality score",
    ]
    assert [metric.value for metric in app.metric] == ["33", "3", "87.88"]
    assert len(app.dataframe) == 2
    assert app.dataframe[0].value["Triggered"].tolist() == [4, 4, 4]
    assert app.dataframe[1].value["Respondent"].tolist() == [str(idno) for idno in FLAGGED_IDS]
    assert app.download_button[0].label == "Download diagnostic report"

    app.download_button[0].click().run()
    assert [metric.value for metric in app.metric] == ["33", "3", "87.88"]
    assert len(app.success) == 0

    app.sidebar.file_uploader[1].upload("rules.json", b"{not json", "application/json").run()
    assert len(app.metric) == 0
    app.sidebar.button[0].click().run()
    assert app.error[0].value.startswith("Error: Could not read rules JSON")
    assert len(app.success) == 0
    assert len(app.metric) == 0
    assert len(app.dataframe) == 0


def test_app_suspicious_only_toggle_filters_flagged_table():
    app = _run_app(FIXTURE_CSV.read_bytes())
    # Arrow serialises the object-typed Respondent column as text.
    all_flagged = [str(idno) for idno in FLAGGED_IDS]

    assert app.toggle[0].label == "Show suspicious respondents only"
    assert not app.toggle[0].value
    assert app.dataframe[1].value["Respondent"].tolist() == all_flagged

    app.toggle[0].set_value(True).run()
    assert app.dataframe[1].value["Respondent"].tolist() == [str(idno) for idno in SUSPICIOUS_IDS]
    assert app.dataframe[1].value["Suspicious"].tolist() == [True, True, True]
    assert [metric.value for metric in app.metric] == ["33", "3", "87.88"]

    app.toggle[0].set_value(False).run()
    assert app.dataframe[1].value["Respondent"].tolist() == all_flagged


def test_app_suspicious_only_toggle_without_suspicious_respondents():
    app = _run_app(FIXTURE_CSV.read_bytes(), rules=_rules_without_suspicious())

    app.toggle[0].set_value(True).run()

    assert len(app.dataframe) == 1
    assert "No respondents are suspicious." in [info.value for info in app.main.info]


def test_app_bar_chart_shows_detector_percentages_in_table_order():
    app = _run_app(FIXTURE_CSV.read_bytes())

    charts = app.get("vega_lite_chart")
    assert len(charts) == 1
    spec = json.loads(charts[0].proto.spec)
    assert spec["mark"]["type"] == "bar"
    assert spec["encoding"]["x"]["field"] == "Detector"
    assert spec["encoding"]["x"]["sort"] is None
    assert spec["encoding"]["y"]["field"] == "Percentage"
    assert spec["encoding"]["y"]["title"] == "Respondents triggered (%)"
    data = convert_arrow_bytes_to_pandas_df(charts[0].proto.datasets[0].data.data)
    assert data["Detector"].tolist() == ["Straightlining", "Contradiction", "Mahalanobis"]
    assert data["Percentage"].tolist() == pytest.approx(app.dataframe[0].value["Percentage"].tolist())


def test_app_offers_report_and_cleaned_data_downloads():
    app = _run_app(FIXTURE_CSV.read_bytes(), "wave1.csv")

    assert [button.label for button in app.download_button] == [
        "Download diagnostic report",
        "Download cleaned data (CSV)",
    ]
    assert "Cleaned data: removed 3 suspicious respondents, kept 30." in [
        caption.value for caption in app.caption
    ]
    app.download_button[1].click().run()
    assert [metric.value for metric in app.metric] == ["33", "3", "87.88"]
