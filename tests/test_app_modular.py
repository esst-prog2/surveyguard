import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app import BUNDLED_RULES, bundled_rules_files, run_surveyguard
from surveyguard.config import load_rules
from surveyguard.errors import ConfigurationError


APP_PATH = Path(__file__).resolve().parent.parent / "app.py"
ESS_RULES = Path("config/scale_logic.json")
ESS_MOCK_CSV = Path("tests/fixtures/ess_mock.csv")
ESS2_RULES = Path("config/ess2.json")
ESS2_MOCK_CSV = Path("tests/fixtures/ess2_mock.csv")
INCLUDE_ERROR = "Error: include is not supported for uploaded rules files"


def _app() -> AppTest:
    return AppTest.from_file(str(APP_PATH), default_timeout=60).run()


def _choose_bundled(app: AppTest, name: str) -> AppTest:
    app.sidebar.radio[0].set_value(BUNDLED_RULES).run()
    options = [path.name for path in bundled_rules_files()]
    app.sidebar.selectbox[0].select_index(options.index(name)).run()
    return app


def test_bundled_rules_files_are_the_top_level_configs():
    assert [path.name for path in bundled_rules_files()] == [
        *(f"ess{round_number}.json" for round_number in range(1, 12)), "scale_logic.json", "spike_logic.json",
    ]


def test_app_offers_every_ess_round_in_natural_order():
    app = _app()
    app.sidebar.radio[0].set_value(BUNDLED_RULES).run()

    assert app.sidebar.selectbox[0].options == [
        *(f"config/ess{round_number}.json" for round_number in range(1, 12)),
        "config/scale_logic.json",
        "config/spike_logic.json",
    ]


def test_bundled_rules_match_uploaded_rules():
    uploaded = run_surveyguard("wave1.csv", ESS_MOCK_CSV.read_bytes(), ESS_RULES.read_bytes())
    bundled = run_surveyguard("wave1.csv", ESS_MOCK_CSV.read_bytes(), rules_path=ESS_RULES)

    assert bundled.report_bytes == uploaded.report_bytes
    assert bundled.cleaned_csv == uploaded.cleaned_csv
    pd.testing.assert_frame_equal(bundled.scales, uploaded.scales)


def test_bundled_modular_rules_match_cli_report(tmp_path):
    report_path = tmp_path / "ess2.md"
    cli = subprocess.run(
        [
            sys.executable, "detect_anomalies.py", str(ESS2_MOCK_CSV), "--rules", str(ESS2_RULES),
            "--output", str(tmp_path / "scored.csv"), "--report", str(report_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert cli.returncode == 0, cli.stdout + cli.stderr

    result = run_surveyguard("ess2_mock.csv", ESS2_MOCK_CSV.read_bytes(), rules_path=ESS2_RULES)

    assert result.report_bytes == report_path.read_bytes()
    assert result.scales["Scale"].tolist() == list(load_rules(ESS2_RULES).scales)


def test_uploaded_rules_with_include_are_rejected():
    with pytest.raises(ConfigurationError, match="include is not supported for uploaded rules files"):
        run_surveyguard("survey.csv", ESS2_MOCK_CSV.read_bytes(), ESS2_RULES.read_bytes())


def test_exactly_one_rules_source_is_required():
    with pytest.raises(ValueError, match="exactly one"):
        run_surveyguard("survey.csv", ESS_MOCK_CSV.read_bytes())
    with pytest.raises(ValueError, match="exactly one"):
        run_surveyguard("survey.csv", ESS_MOCK_CSV.read_bytes(), ESS_RULES.read_bytes(), rules_path=ESS_RULES)


def test_app_runs_with_data_and_a_bundled_rules_file():
    app = _app()
    assert [radio.value for radio in app.sidebar.radio] == ["Upload a rules file"]

    _choose_bundled(app, "scale_logic.json")
    assert len(app.sidebar.file_uploader) == 1
    assert app.sidebar.button[0].disabled
    assert app.sidebar.info[0].value == "Upload the response data file to run SurveyGuard."

    app.sidebar.file_uploader[0].upload("survey.csv", ESS_MOCK_CSV.read_bytes(), "text/csv").run()
    assert not app.sidebar.button[0].disabled
    app.sidebar.button[0].click().run()

    assert not app.exception
    assert len(app.error) == 0
    assert [metric.value for metric in app.metric] == ["33", "3", "87.88"]


def test_app_scale_table_matches_report():
    app = _choose_bundled(_app(), "scale_logic.json")
    app.sidebar.file_uploader[0].upload("survey.csv", ESS_MOCK_CSV.read_bytes(), "text/csv").run()
    app.sidebar.button[0].click().run()

    expected = run_surveyguard("survey.csv", ESS_MOCK_CSV.read_bytes(), rules_path=ESS_RULES).scales
    shown = app.dataframe[2].value
    assert shown.columns.tolist() == expected.columns.tolist()
    assert shown.astype(str).values.tolist() == expected.astype(str).values.tolist()
    assert "Mahalanobis counts respondents flagged on at least 1 scale(s)." in [caption.value for caption in app.caption]


def test_app_names_skipped_scales_and_rules():
    rules = load_rules(ESS2_RULES)
    rotating = [name for name, scale in rules.scales.items() if not scale.required]
    columns = [column for name in rotating for column in rules.scales[name].columns] + ["dsgrhwk", "dsgrmny"]
    core_only = pd.read_csv(ESS2_MOCK_CSV).drop(columns=columns)
    skipped_rules = [rule.label for rule in rules.contradictions if set(rule.columns) & set(columns)]

    app = _choose_bundled(_app(), "ess2.json")
    app.sidebar.file_uploader[0].upload("core.csv", core_only.to_csv(index=False).encode("utf-8"), "text/csv").run()
    app.sidebar.button[0].click().run()

    assert not app.exception
    skipped = [info.value for info in app.main.info if info.value.startswith("Skipped scales:")]
    assert skipped == [f"Skipped scales: {', '.join(rotating)}. Skipped contradiction rules: {'; '.join(skipped_rules)}."]


def test_app_rejects_uploaded_rules_with_include():
    app = _app()
    app.sidebar.file_uploader[0].upload("survey.csv", ESS2_MOCK_CSV.read_bytes(), "text/csv").run()
    app.sidebar.file_uploader[1].upload("ess2.json", ESS2_RULES.read_bytes(), "application/json").run()
    app.sidebar.button[0].click().run()

    assert not app.exception
    assert app.error[0].value.startswith(INCLUDE_ERROR)
    assert len(app.metric) == 0
    assert len(app.dataframe) == 0


def test_app_switching_rules_source_clears_results():
    app = _app()
    app.sidebar.file_uploader[0].upload("survey.csv", ESS_MOCK_CSV.read_bytes(), "text/csv").run()
    app.sidebar.file_uploader[1].upload("rules.json", ESS_RULES.read_bytes(), "application/json").run()
    app.sidebar.button[0].click().run()
    assert len(app.metric) == 3

    _choose_bundled(app, "scale_logic.json")

    assert len(app.metric) == 0
    assert not app.sidebar.button[0].disabled
