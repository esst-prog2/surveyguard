import json
from pathlib import Path

import pandas as pd
import pyreadstat
import pytest
from streamlit.testing.v1 import AppTest

from app import BUNDLED_RULES, bundled_rules_files
from surveyguard.cli import main
from surveyguard.config import load_rules
from surveyguard.errors import ConfigurationError, DataValidationError
from surveyguard.io import load_input
from surveyguard.scoring import score_run


APP_PATH = Path(__file__).resolve().parent.parent / "app.py"
THREE_SCALES_CSV = Path("tests/fixtures/three_scales.csv")
THREE_SCALES_RULES = Path("tests/fixtures/rules/three_scales.json")


def _rules(tmp_path, **root) -> Path:
    data = json.loads(THREE_SCALES_RULES.read_text(encoding="utf-8"))
    data.update(root)
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _data(tmp_path, essround=None) -> Path:
    frame = pd.read_csv(THREE_SCALES_CSV)
    if essround is not None:
        frame["essround"] = essround
    path = tmp_path / "survey.csv"
    frame.to_csv(path, index=False)
    return path


def test_matching_round_scores_like_rules_without_the_key(tmp_path):
    checked = load_rules(_rules(tmp_path, essround=3))
    rounds = [3] * len(pd.read_csv(THREE_SCALES_CSV))
    rounds[5] = None  # a missing round value is ignored
    data = _data(tmp_path, rounds)

    scored = score_run(load_input(data, checked), checked).scored
    unchecked = load_rules(THREE_SCALES_RULES)

    pd.testing.assert_frame_equal(scored, score_run(load_input(data, unchecked), unchecked).scored)


def test_different_round_is_a_structural_error(tmp_path):
    rules = load_rules(_rules(tmp_path, essround=3))

    with pytest.raises(DataValidationError, match=r"^Rules file expects ESS round 3, but the data contains essround 4$"):
        load_input(_data(tmp_path, 4), rules)


def test_mixed_rounds_are_listed_in_numeric_order(tmp_path):
    rules = load_rules(_rules(tmp_path, essround=3))
    rows = len(pd.read_csv(THREE_SCALES_CSV))

    with pytest.raises(DataValidationError, match=r"contains essround 3, 4, 10$"):
        load_input(_data(tmp_path, [10, 4.0, 4] + [3] * (rows - 3)), rules)


def test_missing_round_column_is_a_structural_error(tmp_path):
    rules = load_rules(_rules(tmp_path, essround=3))

    with pytest.raises(DataValidationError, match=r"^Rules file expects ESS round 3, but the data has no essround column$"):
        load_input(_data(tmp_path), rules)


def test_empty_round_column_is_a_structural_error(tmp_path):
    rules = load_rules(_rules(tmp_path, essround=3))

    with pytest.raises(DataValidationError, match=r"^Rules file expects ESS round 3, but the data contains no essround value$"):
        load_input(_data(tmp_path, [None] * len(pd.read_csv(THREE_SCALES_CSV))), rules)


@pytest.mark.parametrize("essround", [4, None])
def test_rules_without_the_key_do_not_check_the_round(tmp_path, essround):
    rules = load_rules(THREE_SCALES_RULES)

    assert rules.essround is None
    assert len(load_input(_data(tmp_path, essround), rules)) == len(pd.read_csv(THREE_SCALES_CSV))


def test_spss_round_double_matches_the_integer_key(tmp_path):
    frame = pd.read_csv(THREE_SCALES_CSV).drop(columns="id")
    frame["essround"] = 2
    path = tmp_path / "survey.sav"
    pyreadstat.write_sav(frame, path)
    rules = load_rules(_rules(tmp_path, essround=2, id_column=None))

    loaded = load_input(path, rules)

    assert loaded["essround"].tolist() == [2.0] * len(frame)


def test_round_key_in_an_included_file_is_rejected(tmp_path):
    module = json.loads(THREE_SCALES_RULES.read_text(encoding="utf-8"))
    (tmp_path / "modules").mkdir()
    (tmp_path / "modules" / "scales.json").write_text(
        json.dumps({"scales": module["scales"], "essround": 3}), encoding="utf-8"
    )
    root = tmp_path / "root.json"
    root.write_text(json.dumps({"include": ["modules/scales.json"]}), encoding="utf-8")

    with pytest.raises(ConfigurationError, match=r"'essround' may only be set in the root rules file, not in included file modules/scales.json"):
        load_rules(root)


@pytest.mark.parametrize("value", [0, -1, "3", 2.5, True])
def test_invalid_round_value_is_rejected(tmp_path, value):
    with pytest.raises(ConfigurationError, match=r"^essround must be a positive integer$"):
        load_rules(_rules(tmp_path, essround=value))


def test_cli_reports_the_round_error_without_output(tmp_path, capsys):
    output = tmp_path / "scored.csv"

    assert main([str(_data(tmp_path, 4)), "--rules", str(_rules(tmp_path, essround=3)), "--output", str(output)]) == 1

    assert "Rules file expects ESS round 3, but the data contains essround 4" in capsys.readouterr().out
    assert not output.exists()


def test_app_shows_the_round_error_for_a_bundled_rules_file():
    rules = load_rules("config/ess3.json")
    columns = [column for scale in rules.scales.values() if scale.required for column in scale.columns]
    columns += [name for name, variable in rules.variables.items() if variable.required]
    frame = pd.DataFrame({"idno": [1, 2, 3], "essround": [4, 4, 4], **{column: [1, 1, 1] for column in columns}})

    app = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
    app.sidebar.radio[0].set_value(BUNDLED_RULES).run()
    names = [path.name for path in bundled_rules_files()]
    app.sidebar.selectbox[0].select_index(names.index("ess3.json")).run()
    app.sidebar.file_uploader[0].upload("ess4.csv", frame.to_csv(index=False).encode("utf-8"), "text/csv").run()
    app.sidebar.button[0].click().run()

    assert not app.exception
    assert app.error[0].value == "Error: Rules file expects ESS round 3, but the data contains essround 4"
    assert len(app.metric) == 0
