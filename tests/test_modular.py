import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from surveyguard.cli import main
from surveyguard.config import load_rules
from surveyguard.errors import ConfigurationError, DataValidationError
from surveyguard.io import load_input, resolve_rules
from surveyguard.reporting import print_summary, render_report, scale_results
from surveyguard.scoring import score_dataframe, score_run


RULES_DIR = Path("tests/fixtures/rules")
THREE_SCALES_CSV = Path("tests/fixtures/three_scales.csv")
THREE_SCALES_RULES = RULES_DIR / "three_scales.json"
ESS_MOCK_CSV = Path("tests/fixtures/ess_mock.csv")
ESS_RULES = Path("config/scale_logic.json")
ESS2_MOCK_CSV = Path("tests/fixtures/ess2_mock.csv")
ESS2_RULES = Path("config/ess2.json")
ROTATING_SCALES = [
    "Medicine_Approval", "Doctor_Attitudes", "Civic_Norms", "Trust_Honest_Dealing", "Wrongness_Judgements",
    "Law_Business_Attitudes", "Wellbeing_Two_Weeks", "Gender_Family_Attitudes", "Housework_Feelings",
    "Job_Characteristics", "Job_Demands", "Work_Family_Conflict", "Study_Conditions", "Job_Choice_Importance",
]


def _write(tmp_path, data: dict, name: str = "rules.json") -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _scale(columns, **extra) -> dict:
    return {"columns": columns, "valid_min": 1, "valid_max": 5, "mahalanobis_threshold": 10.0, **extra}


def _three_scales(tmp_path, **root) -> tuple[pd.DataFrame, object]:
    data = json.loads(THREE_SCALES_RULES.read_text(encoding="utf-8"))
    data.update(root)
    rules = load_rules(_write(tmp_path, data))
    return score_run(load_input(THREE_SCALES_CSV, rules), rules), rules


def _row(scored: pd.DataFrame, respondent: str) -> pd.Series:
    return scored.set_index("id").loc[respondent]


# Include files


def test_include_chain_matches_single_file():
    chained = load_rules(RULES_DIR / "root.json")

    assert list(chained.scales) == ["S1", "S2", "S3"]
    assert chained == load_rules(THREE_SCALES_RULES)


def test_circular_include_is_rejected():
    with pytest.raises(ConfigurationError, match=r"Circular include: circular_a\.json -> circular_b\.json -> circular_a\.json"):
        load_rules(RULES_DIR / "circular_a.json")


def test_file_included_twice_is_rejected(tmp_path):
    _write(tmp_path, {"scales": {"S1": _scale(["a1", "a2"])}}, "shared.json")
    _write(tmp_path, {"include": ["shared.json"]}, "middle.json")
    root = _write(tmp_path, {"include": ["shared.json", "middle.json"], "scales": {"S2": _scale(["b1", "b2"])}})

    with pytest.raises(ConfigurationError, match=r"Rules file shared\.json is included more than once"):
        load_rules(root)


def test_scale_defined_in_two_files_names_both_files():
    with pytest.raises(
        ConfigurationError,
        match=r"Scale 'S1' is defined in both conflicts/scale_s1_a\.json and conflicts/scale_s1_b\.json",
    ):
        load_rules(RULES_DIR / "conflict_scale.json")


def test_column_in_two_files_names_both_scales_and_files():
    with pytest.raises(
        ConfigurationError,
        match=r"Column 'a1' belongs to both scale 'S1' \(conflicts/scale_s1_a\.json\) and scale 'S9' \(conflicts/column_a1\.json\)",
    ):
        load_rules(RULES_DIR / "conflict_column.json")


@pytest.mark.parametrize(
    ("root", "key", "included"),
    [
        ("included_flag_threshold.json", "flag_threshold", "invalid/flag_threshold.json"),
        ("included_min_scales.json", "mahalanobis_min_scales", "invalid/min_scales.json"),
    ],
)
def test_root_only_key_in_included_file_is_rejected(root, key, included):
    with pytest.raises(ConfigurationError, match=rf"'{key}' may only be set in the root rules file, not in included file {included}"):
        load_rules(RULES_DIR / root)


def test_legacy_key_in_included_file_is_rejected():
    with pytest.raises(ConfigurationError, match=r"Legacy rules key 'thresholds'.*invalid/legacy\.json"):
        load_rules(RULES_DIR / "included_legacy.json")


def test_unreadable_included_file_is_rejected():
    with pytest.raises(ConfigurationError, match=r"Could not read included rules file invalid/does_not_exist\.json"):
        load_rules(RULES_DIR / "missing_include.json")


def test_include_can_be_disallowed():
    with pytest.raises(ConfigurationError, match="include is not supported for uploaded rules files"):
        load_rules(RULES_DIR / "root.json", allow_include=False)


@pytest.mark.parametrize("value", [0, 2.5, "3", True])
def test_invalid_mahalanobis_min_scales_is_rejected(tmp_path, value):
    data = json.loads(THREE_SCALES_RULES.read_text(encoding="utf-8"))
    data["mahalanobis_min_scales"] = value

    with pytest.raises(ConfigurationError, match="mahalanobis_min_scales must be a positive integer"):
        load_rules(_write(tmp_path, data))


# Scale settings and alpha thresholds


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"detectors": []}, "detectors must be a non-empty list"),
        ({"detectors": ["irv"]}, "detectors must be a non-empty list"),
        ({"detectors": ["straightlining", "straightlining"]}, "detectors must be a non-empty list"),
        ({"min_items_straightlining": 0}, "min_items_straightlining must be a positive integer"),
        ({"min_items_straightlining": 2.5}, "min_items_straightlining must be a positive integer"),
        ({"mahalanobis_min_rows_per_item": -1}, "mahalanobis_min_rows_per_item must not be negative"),
        ({"mahalanobis_min_rows_per_item": "10"}, "mahalanobis_min_rows_per_item must be numeric"),
        ({"required": "no"}, "required must be true or false"),
        ({"module": ""}, "module must be a non-empty string"),
    ],
)
def test_invalid_scale_settings_are_rejected(tmp_path, changes, message):
    with pytest.raises(ConfigurationError, match=rf"scales\.S1\.{message}"):
        load_rules(_write(tmp_path, {"scales": {"S1": _scale(["a1", "a2"], **changes)}}))


def test_alpha_matches_the_configured_reference_threshold(tmp_path):
    data = json.loads(ESS_RULES.read_text(encoding="utf-8"))
    del data["scales"]["Trust_Institutions"]["mahalanobis_threshold"]
    data["scales"]["Trust_Institutions"]["mahalanobis_alpha"] = 0.05
    rules = load_rules(_write(tmp_path, data))
    scale = rules.scales["Trust_Institutions"]

    assert round(scale.mahalanobis_threshold, 6) == 11.070498
    assert scale.threshold_source == "alpha=0.05"
    derived = score_dataframe(load_input(ESS_MOCK_CSV, rules), rules)
    reference = score_dataframe(load_input(ESS_MOCK_CSV, load_rules(ESS_RULES)), load_rules(ESS_RULES))
    pd.testing.assert_frame_equal(derived, reference)


def test_alpha_for_four_items(tmp_path):
    rules = load_rules(_write(tmp_path, {"scales": {"S1": {
        "columns": ["a1", "a2", "a3", "a4"], "valid_min": 1, "valid_max": 5, "mahalanobis_alpha": 0.01,
    }}}))

    assert round(rules.scales["S1"].mahalanobis_threshold, 6) == 13.276704
    assert rules.scales["S1"].threshold_source == "alpha=0.01"


@pytest.mark.parametrize(
    ("scale", "message"),
    [
        (_scale(["a1", "a2"], mahalanobis_alpha=0.05), "Scale 'S1' defines both mahalanobis_threshold and mahalanobis_alpha"),
        ({"columns": ["a1", "a2"], "valid_min": 1, "valid_max": 5}, r"scales\.S1\.mahalanobis_threshold must be numeric, or define"),
        (
            {"columns": ["a1", "a2"], "valid_min": 1, "valid_max": 5, "detectors": ["straightlining"], "mahalanobis_alpha": 0.05},
            "Scale 'S1' has no Mahalanobis detector",
        ),
        ({"columns": ["a1", "a2"], "valid_min": 1, "valid_max": 5, "mahalanobis_alpha": 1}, "mahalanobis_alpha must be between 0 and 1"),
    ],
)
def test_threshold_and_alpha_combinations_are_validated(tmp_path, scale, message):
    with pytest.raises(ConfigurationError, match=message):
        load_rules(_write(tmp_path, {"scales": {"S1": scale}}))


def test_scale_without_mahalanobis_needs_no_threshold(tmp_path):
    rules = load_rules(_write(tmp_path, {"scales": {"S1": {
        "columns": ["a1", "a2"], "valid_min": 1, "valid_max": 5, "detectors": ["straightlining"],
    }}}))

    assert rules.scales["S1"].mahalanobis_threshold is None


# Rule-only variables


def _variable_rules(tmp_path, **extra) -> object:
    return load_rules(_write(tmp_path, {
        # Four rows cannot support a covariance matrix, so these tests only use straightlining.
        "scales": {"S1": {"columns": ["a1", "a2", "a3"], "valid_min": 1, "valid_max": 5, "detectors": ["straightlining"]}},
        "variables": {
            "partner": {"valid_min": 1, "valid_max": 2, "missing_codes": [9]},
            "dsgrhwk": {"valid_min": 1, "valid_max": 7, "missing_codes": [66, 77, 88, 99]},
            "rshipa2": {"valid_min": 1, "valid_max": 6, "missing_codes": [66, 77, 88, 99]},
        },
        "contradictions": [
            {"conditions": [{"column": "partner", "op": "==", "value": 2}, {"column": "dsgrhwk", "op": ">=", "value": 1}]},
            {"conditions": [{"column": "partner", "op": "==", "value": 2}, {"column": "rshipa2", "op": "==", "value": 1}]},
        ],
        **extra,
    }))


def _variable_frame() -> pd.DataFrame:
    return pd.DataFrame({
        "a1": [1, 2, 3, 4], "a2": [2, 3, 4, 5], "a3": [3, 2, 5, 4],
        "partner": [2, 1, 2, 2], "dsgrhwk": [3, 66, 66, 66], "rshipa2": [3, 1, 66, 1],
    })


def test_rule_on_rule_only_variable_triggers(tmp_path):
    rules = _variable_rules(tmp_path)
    scored = score_dataframe(_variable_frame(), rules)

    assert scored.loc[0, "flag_reasons"] == "Contradiction: partner==2 vs dsgrhwk>=1"
    assert scored.loc[3, "flag_reasons"] == "Contradiction: partner==2 vs rshipa2==1"


def test_variable_missing_code_skips_rule_without_data_quality_marker(tmp_path):
    rules = _variable_rules(tmp_path)
    scored = score_dataframe(_variable_frame(), rules)

    assert scored.loc[2, "flag_reasons"] == ""
    assert not scored.loc[2, "logical_contradiction_available"]
    assert scored["data_quality"].tolist() == ["", "", "", ""]


def test_variable_sharing_a_scale_column_is_rejected(tmp_path):
    data = {"scales": {"S1": _scale(["a1", "a2"])}, "variables": {"a1": {"valid_min": 1, "valid_max": 5}}}

    with pytest.raises(ConfigurationError, match="Column 'a1' belongs to both scale 'S1' and variable 'a1'"):
        load_rules(_write(tmp_path, data))


def test_rule_on_undeclared_column_names_position_and_file(tmp_path):
    data = {
        "scales": {"S1": _scale(["a1", "a2"])},
        "contradictions": [{"conditions": [{"column": "a1", "op": ">", "value": 4}, {"column": "agea", "op": "<", "value": 20}]}],
    }

    with pytest.raises(
        ConfigurationError,
        match=r"contradictions\[0\]\.conditions\[1\]\.column 'agea' must belong to a configured scale or be a declared variable \(in rules\.json\)",
    ):
        load_rules(_write(tmp_path, data))


# Optional scales and variables


def _optional_rules(tmp_path) -> object:
    return load_rules(_write(tmp_path, {
        "scales": {
            "Core": _scale(["a1", "a2", "a3"]),
            "Rotating": _scale(["r1", "r2", "r3"], required=False, module="rotating"),
        },
        "variables": {"rv": {"valid_min": 1, "valid_max": 5, "required": False}},
        "contradictions": [
            {"conditions": [{"column": "a1", "op": ">", "value": 4}, {"column": "a2", "op": "<", "value": 2}]},
            {"conditions": [{"column": "a1", "op": ">", "value": 4}, {"column": "r1", "op": "<", "value": 2}]},
            {"conditions": [{"column": "a1", "op": ">", "value": 4}, {"column": "rv", "op": "<", "value": 2}]},
        ],
    }))


CORE_ONLY = pd.DataFrame({"a1": [5, 2, 3, 4, 1], "a2": [1, 3, 4, 5, 2], "a3": [3, 2, 5, 4, 1]})


def test_absent_optional_scale_is_skipped_and_listed(tmp_path):
    run = score_run(CORE_ONLY, _optional_rules(tmp_path))

    assert run.skipped_scales == ("Rotating",)
    assert [scale.name for scale in run.scales] == ["Core"]
    assert "mahalanobis_distance_Rotating" not in run.scored.columns
    assert [rule.label for rule in run.skipped_rules] == [
        "Contradiction: a1>4 vs r1<2",
        "Contradiction: a1>4 vs rv<2",
    ]
    assert run.scored.loc[0, "flag_reasons"] == "Contradiction: a1>4 vs a2<2"


def test_partly_present_optional_scale_is_an_error(tmp_path):
    frame = CORE_ONLY.assign(r1=[1, 2, 3, 4, 5])

    with pytest.raises(
        DataValidationError,
        match="Optional scale 'Rotating' is only partly present in the input; missing columns: r2, r3",
    ):
        resolve_rules(_optional_rules(tmp_path), frame.columns)


def test_missing_required_scale_column_keeps_the_former_message(tmp_path):
    with pytest.raises(DataValidationError, match="Missing configured question columns: a3"):
        resolve_rules(_optional_rules(tmp_path), ["a1", "a2"])


def test_every_scale_skipped_is_an_error(tmp_path):
    rules = load_rules(_write(tmp_path, {"scales": {"Rotating": _scale(["r1", "r2"], required=False)}}))

    with pytest.raises(DataValidationError, match="No configured scale is present in the input"):
        resolve_rules(rules, ["idno"])


def test_required_variable_is_checked(tmp_path):
    rules = _variable_rules(tmp_path)

    with pytest.raises(DataValidationError, match="Missing configured variable columns: dsgrhwk"):
        resolve_rules(rules, ["a1", "a2", "a3", "partner", "rshipa2"])


# Detector settings


def test_short_scale_does_not_straightline_and_detector_is_unavailable(tmp_path):
    rules = load_rules(_write(tmp_path, {"scales": {"Short": _scale(["a1", "a2", "a3"], min_items_straightlining=5)}}))
    frame = pd.DataFrame({"a1": [4, 1, 2], "a2": [4, 2, 3], "a3": [4, 3, 5]})
    scored = score_dataframe(frame, rules)

    assert scored.loc[0, "flag_reasons"] == ""
    assert not scored["straightlining_available"].any()


def test_straightlining_can_be_switched_off(tmp_path):
    rules = load_rules(_write(tmp_path, {"scales": {"Long": _scale(
        ["a1", "a2", "a3", "a4", "a5"], detectors=["mahalanobis_outlier"],
    )}}))
    frame = pd.DataFrame({
        "a1": [1, 2, 3, 4, 5, 2, 3], "a2": [1, 3, 2, 5, 4, 4, 1], "a3": [1, 4, 5, 2, 3, 1, 2],
        "a4": [1, 5, 4, 3, 2, 3, 4], "a5": [1, 2, 1, 4, 5, 5, 3],
    })
    run = score_run(frame, rules)

    assert "Straightlining_Long" not in run.scored.loc[0, "flag_reasons"]
    assert not run.scored["straightlining_available"].any()
    assert run.scored["mahalanobis_outlier_available"].all()
    assert run.scales[0].detectors == ("mahalanobis_outlier",)


def _rows_for_four_items(count: int) -> pd.DataFrame:
    return pd.DataFrame({
        "a1": [1 + index % 5 for index in range(count)],
        "a2": [1 + (index * 2) % 5 for index in range(count)],
        "a3": [1 + (index * 3 + 1) % 5 for index in range(count)],
        "a4": [1 + (index // 5) % 5 for index in range(count)],
    })


@pytest.mark.parametrize(("count", "available"), [(39, False), (40, True)])
def test_minimum_valid_rows_per_item(tmp_path, count, available):
    rules = load_rules(_write(tmp_path, {"scales": {"S1": _scale(
        ["a1", "a2", "a3", "a4"], mahalanobis_min_rows_per_item=10,
    )}}))
    run = score_run(_rows_for_four_items(count), rules)

    assert run.scored["mahalanobis_distance_S1"].notna().all() == available
    assert run.scored["mahalanobis_outlier_available"].all() == available
    expected = "available" if available else f"not available ({count} valid rows, needs 40)"
    assert run.scales[0].mahalanobis_status == expected


def test_default_minimum_needs_two_rows(tmp_path):
    # A one-item scale keeps the two-row covariance invertible.
    rules = load_rules(_write(tmp_path, {"scales": {"S1": _scale(["a1"])}}))
    run = score_run(pd.DataFrame({"a1": [1, 3]}), rules)

    assert run.scored["mahalanobis_distance_S1"].notna().all()
    assert run.scales[0].required_rows == 2


# Minimum number of flagged Mahalanobis scales


def test_two_flagged_scales_below_minimum_are_not_triggered(tmp_path):
    run, _ = _three_scales(tmp_path)
    row = _row(run.scored, "o2")

    assert not row["mahalanobis_outlier_triggered"]
    assert row["flag_reasons"] == ""
    assert json.loads(row["detector_details"])["mahalanobis_outlier"]["flagged_scales"] == ["S1", "S2"]
    assert row["quality_score"] == 100.0


def test_minimum_number_of_flagged_scales_reached(tmp_path):
    run, _ = _three_scales(tmp_path)
    row = _row(run.scored, "o3")

    assert row["mahalanobis_outlier_triggered"]
    assert row["flag_reasons"] == "Mahalanobis_S1;Mahalanobis_S2;Mahalanobis_S3"
    assert round(row["quality_score"], 2) == 66.67


def test_fewer_evaluable_scales_than_minimum(tmp_path):
    run, _ = _three_scales(tmp_path)
    row = _row(run.scored, "o2m")

    assert pd.isna(row["mahalanobis_distance_S3"])
    assert row["mahalanobis_outlier_available"]
    assert not row["mahalanobis_outlier_triggered"]
    assert row["quality_score"] == 100.0


def test_default_minimum_keeps_any_scale_behaviour(tmp_path):
    run, _ = _three_scales(tmp_path, mahalanobis_min_scales=1)
    scored = run.scored.set_index("id")

    assert scored.loc["o2", "flag_reasons"] == "Mahalanobis_S1;Mahalanobis_S2"
    assert scored.loc["o2m", "flag_reasons"] == "Mahalanobis_S1;Mahalanobis_S2"
    assert scored.loc[["o2", "o3", "o2m"], "quality_score"].round(2).tolist() == [66.67, 66.67, 66.67]
    assert scored["mahalanobis_outlier_triggered"].sum() == 3
    assert "flagged_scales" not in json.loads(scored.loc["o2", "detector_details"])["mahalanobis_outlier"]


@pytest.mark.parametrize("minimum", [1, 3])
def test_scale_level_counts_do_not_depend_on_minimum(tmp_path, minimum):
    run, _ = _three_scales(tmp_path, mahalanobis_min_scales=minimum)

    assert [(scale.name, scale.mahalanobis_count, scale.valid_rows) for scale in run.scales] == [
        ("S1", 3, 27),
        ("S2", 3, 27),
        ("S3", 1, 26),
    ]


def test_report_separates_respondent_and_scale_level_mahalanobis_counts(tmp_path):
    run, rules = _three_scales(tmp_path)
    report = render_report(run.scored, rules.id_column, run)

    assert "| Mahalanobis | 1 | 3.70% |" in report
    assert "Mahalanobis counts respondents flagged on at least 3 scale(s)." in report
    assert "| Scale | Module | Items | Detectors | Threshold | Valid rows | Straightlining | Mahalanobis flags (scale-level) | Status |" in report
    assert "| S1 | - | 3 | straightlining, mahalanobis_outlier | 8.000000 (configured) | 27 | 0 | 3 | available |" in report
    assert "| S3 | - | 3 | straightlining, mahalanobis_outlier | 8.000000 (configured) | 26 | 0 | 1 | available |" in report


# Single-scale and fixture regressions


def test_spike_output_schema_is_unchanged():
    rules = load_rules("config/spike_logic.json")
    scored = score_dataframe(pd.read_csv("spike_data.csv"), rules)

    assert list(scored.columns)[10:] == [
        "quality_score", "suspicious", "flag_reasons", "data_quality",
        "straightlining_triggered", "straightlining_available",
        "logical_contradiction_triggered", "logical_contradiction_available",
        "mahalanobis_outlier_triggered", "mahalanobis_outlier_available",
        "mahalanobis_distance_Extraversion", "detector_details",
    ]
    details = json.loads(scored.loc[0, "detector_details"])
    assert list(details["mahalanobis_outlier"]) == ["available", "distances"]


def test_ess_mock_scale_results():
    rules = load_rules(ESS_RULES)
    table = scale_results(score_run(load_input(ESS_MOCK_CSV, rules), rules))

    assert table.to_dict("records") == [
        {
            "Scale": "Trust_Institutions", "Module": "-", "Items": 5,
            "Detectors": "straightlining, mahalanobis_outlier", "Threshold": "11.070498 (configured)",
            "Valid rows": 31, "Straightlining": 2, "Mahalanobis flags (scale-level)": 3, "Status": "available",
        },
        {
            "Scale": "Satisfaction", "Module": "-", "Items": 4,
            "Detectors": "straightlining, mahalanobis_outlier", "Threshold": "9.487729 (configured)",
            "Valid rows": 31, "Straightlining": 3, "Mahalanobis flags (scale-level)": 2, "Status": "available",
        },
    ]


def test_alpha_threshold_row_in_report(tmp_path):
    data = {"scales": {"S5": {
        "columns": ["a1", "a2", "a3", "a4", "a5"], "valid_min": 1, "valid_max": 5, "mahalanobis_alpha": 0.01,
    }}}
    rules = load_rules(_write(tmp_path, data))
    rng = np.random.default_rng(7)
    frame = pd.DataFrame(rng.integers(1, 6, size=(30, 5)), columns=["a1", "a2", "a3", "a4", "a5"])
    run = score_run(frame, rules)

    assert "| S5 | - | 5 | straightlining, mahalanobis_outlier | 15.086272 (alpha=0.01) |" in render_report(run.scored, None, run)


def test_report_lists_skipped_scales_and_rules(tmp_path):
    run = score_run(CORE_ONLY, _optional_rules(tmp_path))
    report = render_report(run.scored, None, run)

    assert "- Skipped scales: Rotating" in report
    assert "- Skipped contradiction rules: Contradiction: a1>4 vs r1<2; Contradiction: a1>4 vs rv<2" in report


def test_report_without_run_has_no_scale_sections():
    rules = load_rules(ESS_RULES)
    scored = score_dataframe(load_input(ESS_MOCK_CSV, rules), rules)

    assert "## Scale results" not in render_report(scored, rules.id_column)


def test_summary_prints_skipped_scales_only_when_present(tmp_path, capsys):
    run = score_run(CORE_ONLY, _optional_rules(tmp_path))
    print_summary(run.scored, Path("out.csv"), run.skipped_scales)
    assert "Skipped scales: Rotating\n" in capsys.readouterr().out

    print_summary(run.scored, Path("out.csv"))
    assert "Skipped scales" not in capsys.readouterr().out


# Modular ESS round 2 configuration


def test_ess2_configuration_loads_with_documented_settings():
    rules = load_rules(ESS2_RULES)

    assert list(rules.scales) == [
        "Social_Trust", "Trust_Institutions", "Satisfaction", "Policy_Attitudes", "Immigration_Policy",
        "Immigration_Effects", "Job_Autonomy", "Human_Values", *ROTATING_SCALES,
    ]
    assert rules.flag_threshold == 50
    assert rules.mahalanobis_min_scales == 3
    assert rules.id_column == "idno"
    assert len(rules.contradictions) == 24
    for scale in rules.scales.values():
        assert scale.module == ("rotating" if scale.name in ROTATING_SCALES else "core")
        assert scale.required == (scale.name not in ROTATING_SCALES)
        assert scale.threshold_source == "alpha=0.01"
        assert scale.min_items_straightlining == 5
        assert scale.mahalanobis_min_rows_per_item == 10
    straightlining_off = {"Medicine_Approval", "Wellbeing_Two_Weeks", "Gender_Family_Attitudes", "Job_Choice_Importance"}
    assert {name for name, scale in rules.scales.items() if "straightlining" not in scale.detectors} == straightlining_off
    assert rules.variables["dsgrhwk"].required is False
    assert rules.variables["agea"].required is True


def test_ess2_mock_triggers_every_contradiction_rule(tmp_path, capsys):
    report = tmp_path / "ess2.md"
    assert main([str(ESS2_MOCK_CSV), "--rules", str(ESS2_RULES), "--output", str(tmp_path / "ess2.csv"), "--report", str(report)]) == 0

    scored = pd.read_csv(tmp_path / "ess2.csv")
    reasons = scored["flag_reasons"].fillna("").str.split(";")
    for rule in load_rules(ESS2_RULES).contradictions:
        assert reasons.map(lambda values: rule.label in values).any(), rule.label
    assert "Skipped scales" not in capsys.readouterr().out
    assert "| Human_Values | core | 21 | straightlining, mahalanobis_outlier | 38.932173 (alpha=0.01) |" in report.read_text(encoding="utf-8")


def test_ess2_core_only_data_skips_every_rotating_scale(tmp_path, capsys):
    rules = load_rules(ESS2_RULES)
    rotating_columns = [column for name in ROTATING_SCALES for column in rules.scales[name].columns]
    core_only = pd.read_csv(ESS2_MOCK_CSV).drop(columns=rotating_columns + ["dsgrhwk", "dsgrmny"])
    source = tmp_path / "core_only.csv"
    core_only.to_csv(source, index=False)
    report = tmp_path / "core_only.md"

    assert main([str(source), "--rules", str(ESS2_RULES), "--output", str(tmp_path / "scored.csv"), "--report", str(report)]) == 0

    assert f"Skipped scales: {', '.join(ROTATING_SCALES)}\n" in capsys.readouterr().out
    text = report.read_text(encoding="utf-8")
    assert f"- Skipped scales: {', '.join(ROTATING_SCALES)}" in text
    assert "Contradiction: partner==2 vs dsgrhwk>=1" in text.split("## Skipped scales and rules")[1]


def test_ess2_mock_with_partly_missing_rotating_scale_fails(tmp_path, capsys):
    source = tmp_path / "partial.csv"
    pd.read_csv(ESS2_MOCK_CSV).drop(columns=["jbscr", "hlthrwk"]).to_csv(source, index=False)

    assert main([str(source), "--rules", str(ESS2_RULES), "--output", str(tmp_path / "scored.csv")]) == 1

    assert "Optional scale 'Job_Characteristics' is only partly present" in capsys.readouterr().out
    assert not (tmp_path / "scored.csv").exists()
