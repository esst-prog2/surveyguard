import json
from pathlib import Path

import pandas as pd
import pyreadstat
import pytest

from surveyguard.config import load_rules
from surveyguard.detectors import DetectorResult, irv, logical_contradictions, mahalanobis, straightlining
from surveyguard.errors import ConfigurationError, DataValidationError, MathematicalError
from surveyguard.io import load_csv, load_input
from surveyguard.reporting import print_summary, write_report
from surveyguard.scoring import aggregate_score, score_dataframe


FIXTURE_RULES = "tests/fixtures/rules.json"
FIXTURE_CSV = "tests/fixtures/survey.csv"


def test_load_rules_and_reject_malformed_rules(tmp_path):
    rules = load_rules(FIXTURE_RULES)
    assert rules.id_column == "respondent_id"
    assert rules.blocks["attitude_scale"].minimum == 1
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps({"blocks": {"x": {"columns": ["Q1"]}}}), encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_rules(bad_path)

    wrong_pair_path = tmp_path / "wrong_pair.json"
    wrong_pair_path.write_text(json.dumps({
        "blocks": {"x": {"columns": ["Q1", "Q2"], "min": 1, "max": 5}},
        "inverted_pairs": [["Q1", "Q3", "x"]],
    }), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="must belong"):
        load_rules(wrong_pair_path)


@pytest.mark.parametrize("remove_thresholds", [False, True])
def test_missing_mahalanobis_threshold_is_rejected(tmp_path, remove_thresholds):
    rules_data = json.loads(Path(FIXTURE_RULES).read_text(encoding="utf-8"))
    if remove_thresholds:
        del rules_data["thresholds"]
    else:
        del rules_data["thresholds"]["mahalanobis_outlier"]
    rules_path = tmp_path / "missing_threshold.json"
    rules_path.write_text(json.dumps(rules_data), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="thresholds.*mahalanobis_outlier"):
        load_rules(rules_path)


def test_optional_rule_settings_use_documented_defaults(tmp_path):
    rules_path = tmp_path / "defaults.json"
    rules_path.write_text(json.dumps({
        "blocks": {
            "scale": {"columns": ["Q1", "Q2"], "min": 1, "max": 5},
        },
        "thresholds": {"mahalanobis_outlier": 6},
    }), encoding="utf-8")

    rules = load_rules(rules_path)

    assert rules.inverted_pairs == ()
    assert rules.blocks["scale"].high_min == 4
    assert rules.blocks["scale"].low_max == 2
    assert rules.blocks["scale"].irv_threshold == 0
    assert rules.blocks["scale"].missing_values == ()
    assert rules.weights == {
        "straightlining": 1.0,
        "logical_contradiction": 1.0,
        "mahalanobis_outlier": 1.0,
    }
    assert rules.flag_threshold == 50
    assert rules.id_column is None


def test_missing_configured_column_fails_before_scoring(tmp_path):
    rules = load_rules(FIXTURE_RULES)
    csv_path = tmp_path / "missing.csv"
    pd.DataFrame({"respondent_id": ["r1"], "Q1": [1]}).to_csv(csv_path, index=False)
    with pytest.raises(DataValidationError, match="Missing configured question columns"):
        load_csv(csv_path, rules)


def test_load_xlsx_and_uppercase_extension(tmp_path):
    rules = load_rules(FIXTURE_RULES)
    path = tmp_path / "survey.XLSX"
    pd.read_csv(FIXTURE_CSV).to_excel(path, index=False)

    loaded = load_input(path, rules)

    assert pd.to_numeric(loaded["Q1"], errors="coerce").tolist()[:3] == [3, 1, 5]
    assert loaded["respondent_id"].tolist() == ["r1", "r2", "r3", "r4", "r5", "r6", "r7"]


def test_load_sav_preserves_numeric_codes_with_value_labels(tmp_path):
    rules = load_rules(FIXTURE_RULES)
    path = tmp_path / "survey.sav"
    source = pd.DataFrame({
        "respondent_id": ["r1", "r2", "r3"],
        "Q1": [3, 1, 5],
        "Q2": [3, 1, 5],
        "Q3": [3, 1, 5],
        "Q4": [3, 2, 4],
    })
    pyreadstat.write_sav(
        source,
        path,
        variable_value_labels={"Q1": {1: "Disagree", 3: "Neutral", 5: "Agree"}},
    )

    loaded = load_input(path, rules)

    assert loaded["Q1"].tolist()[:3] == [3.0, 1.0, 5.0]
    assert all(isinstance(value, (int, float)) for value in loaded["Q1"])


def test_load_input_rejects_unsupported_extension(tmp_path):
    rules = load_rules(FIXTURE_RULES)
    path = tmp_path / "survey.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(DataValidationError, match="Supported extensions"):
        load_input(path, rules)


def test_irv_and_straightlining():
    rules = load_rules(FIXTURE_RULES)
    row = pd.Series({"Q1": 3, "Q2": 3, "Q3": 3, "Q4": 3})
    assert irv([3, 3, 3, 3]) == 0
    # Population variance: ((1-2)^2 + (2-2)^2 + (3-2)^2) / 3 = 2/3.
    assert irv([1, 2, 3]) == pytest.approx(2 / 3)
    result = straightlining(row, rules.blocks)
    assert result.triggered is True
    assert result.penalty == 1
    assert "Straightlining_Error:attitude_scale" in result.reasons


@pytest.mark.parametrize(
    ("values", "expected"),
    [((4, 5), True), ((4, 4), True), ((1, 2), True), ((2, 2), True), ((3, 4), False)],
)
def test_inverted_pair_bands(values, expected):
    rules = load_rules(FIXTURE_RULES)
    row = pd.Series({"Q1": 3, "Q2": values[0], "Q3": values[1], "Q4": 3})
    result = logical_contradictions(row, rules)
    assert result.triggered is expected
    assert result.penalty == (1.0 if expected else 0.0)
    assert result.reasons == (["Logical_Contradiction:Q2/Q3"] if expected else [])


def test_mahalanobis_centroid_is_zero():
    rows = pd.DataFrame({"Q1": [1, 2, 3, 2], "Q2": [3, 5, 4, 4]})
    distances, triggered = mahalanobis(rows, ("Q1", "Q2"), threshold=100)
    assert distances.loc[3] == pytest.approx(0)
    assert not bool(triggered.any())


def test_mahalanobis_matches_hand_calculated_squared_distances():
    rows = pd.DataFrame({
        "Q1": [0, 2, 0, 2, 1],
        "Q2": [0, 0, 2, 2, 1],
    })

    distances, triggered = mahalanobis(rows, ("Q1", "Q2"), threshold=1.5)

    # The centroid is (1, 1), and sample covariance is the identity matrix.
    # Each corner is therefore at squared distance 1^2 + 1^2 = 2; the centroid is 0.
    assert distances.tolist() == pytest.approx([2, 2, 2, 2, 0])
    assert triggered.tolist() == [True, True, True, True, False]
    _, at_threshold = mahalanobis(rows, ("Q1", "Q2"), threshold=2)
    assert at_threshold.tolist() == [False, False, False, False, False]


def test_singular_covariance_is_controlled():
    rows = pd.DataFrame({"Q1": [1, 2, 3], "Q2": [2, 4, 6]})
    with pytest.raises(MathematicalError, match="singular"):
        mahalanobis(rows, ("Q1", "Q2"), threshold=1)


def test_weighted_aggregate_uses_configured_threshold_at_call_site():
    results = [DetectorResult("straightlining", penalty=1.0, triggered=True, reasons=["x"])]
    score, suspicious, reasons = aggregate_score(results, {"straightlining": 2.0}, flag_threshold=50)
    assert score == 0
    assert suspicious is True
    assert reasons == ["x"]


def test_zero_weighted_detector_remains_visible_without_affecting_score():
    results = [
        DetectorResult(
            "logical_contradiction",
            penalty=1.0,
            triggered=True,
            reasons=["Logical_Contradiction:Q2/Q3"],
        ),
        DetectorResult("straightlining", penalty=0.0),
    ]
    score, suspicious, reasons = aggregate_score(
        results,
        {"logical_contradiction": 0.0, "straightlining": 1.0},
    )

    assert score == 100.0
    assert suspicious is False
    assert reasons == ["Logical_Contradiction:Q2/Q3"]


def test_unavailable_detector_is_excluded_from_weighted_score():
    results = [
        DetectorResult("straightlining", penalty=1.0),
        DetectorResult("mahalanobis_outlier", penalty=0.0, available=False),
    ]

    score, suspicious, _ = aggregate_score(
        results,
        {"straightlining": 1.0, "mahalanobis_outlier": 3.0},
    )

    assert score == 0.0
    assert suspicious is True


def test_custom_flag_threshold_is_used():
    results = [
        DetectorResult("straightlining", penalty=1.0),
        DetectorResult("mahalanobis_outlier", penalty=0.0),
    ]
    score, suspicious, _ = aggregate_score(
        results,
        {"straightlining": 1.0, "mahalanobis_outlier": 3.0},
        flag_threshold=80,
    )
    # Weighted penalty = (1*1 + 0*3) / (1+3) = 0.25; score = 100 * (1-0.25) = 75.
    assert score == pytest.approx(75)
    assert suspicious is True


def test_score_dataframe_preserves_metadata_and_marks_invalid_value():
    rules = load_rules(FIXTURE_RULES)
    frame = load_csv(FIXTURE_CSV, rules)
    scored = score_dataframe(frame, rules)
    assert list(scored["respondent_id"]) == list(frame["respondent_id"])
    assert list(scored["group"]) == list(frame["group"])
    assert {"quality_score", "suspicious", "flag_reasons", "data_quality"}.issubset(scored.columns)
    assert scored.loc[scored["respondent_id"] == "r7", "data_quality"].iloc[0] == "Invalid_Value"


def test_score_dataframe_marks_missing_value_without_imputation():
    rules = load_rules(FIXTURE_RULES)
    frame = pd.DataFrame({"respondent_id": ["missing"], "Q1": [None], "Q2": [3], "Q3": [3], "Q4": [3]})
    scored = score_dataframe(frame, rules)
    assert scored.loc[0, "data_quality"] == "Missing_Value"
    assert pd.isna(scored.loc[0, "mahalanobis_distance"])
    assert not bool(scored.loc[0, "straightlining_available"])
    assert bool(scored.loc[0, "logical_contradiction_available"])
    assert not bool(scored.loc[0, "mahalanobis_outlier_available"])
    assert scored.loc[0, "quality_score"] == 100


def test_configured_missing_and_out_of_range_values_are_excluded_from_detectors(tmp_path):
    rules_data = json.loads(Path(FIXTURE_RULES).read_text(encoding="utf-8"))
    rules_data["blocks"]["attitude_scale"]["missing_values"] = [77, 88, 99]
    rules_path = tmp_path / "ess-rules.json"
    rules_path.write_text(json.dumps(rules_data), encoding="utf-8")
    rules = load_rules(rules_path)
    frame = pd.DataFrame({
        "respondent_id": ["missing-code", "out-of-range"],
        "Q1": [77, 6],
        "Q2": [3, 3],
        "Q3": [3, 3],
        "Q4": [3, 3],
    })

    scored = score_dataframe(frame, rules)

    assert scored.loc[0, "Q1"] == 77
    assert scored.loc[0, "data_quality"] == "Missing_Value"
    assert not bool(scored.loc[0, "straightlining_available"])
    assert pd.isna(scored.loc[0, "mahalanobis_distance"])
    assert scored.loc[1, "data_quality"] == "Invalid_Value"
    assert not bool(scored.loc[1, "straightlining_available"])
    assert pd.isna(scored.loc[1, "mahalanobis_distance"])


def test_score_dataframe_returns_unavailable_score_when_no_detector_can_run(capsys):
    rules = load_rules(FIXTURE_RULES)
    frame = pd.DataFrame({
        "respondent_id": ["unscorable"],
        "Q1": [None],
        "Q2": [None],
        "Q3": [None],
        "Q4": [None],
    })

    scored = score_dataframe(frame, rules)

    assert pd.isna(scored.loc[0, "quality_score"])
    assert pd.isna(scored.loc[0, "suspicious"])
    assert not scored.loc[
        0,
        [
            "straightlining_available",
            "logical_contradiction_available",
            "mahalanobis_outlier_available",
        ],
    ].any()
    print_summary(scored, Path("unscored.csv"))
    summary = capsys.readouterr().out
    assert "Not scored: 1" in summary
    assert "Not scored reason: no positive-weight detector had enough valid responses" in summary


def test_score_dataframe_does_not_dilute_available_detector_with_missing_values():
    rules = load_rules(FIXTURE_RULES)
    frame = pd.DataFrame({
        "respondent_id": ["partial"],
        "Q1": [None],
        "Q2": [4],
        "Q3": [5],
        "Q4": [3],
    })

    scored = score_dataframe(frame, rules)

    assert scored.loc[0, "logical_contradiction_available"]
    assert not scored.loc[0, "straightlining_available"]
    assert not scored.loc[0, "mahalanobis_outlier_available"]
    assert scored.loc[0, "logical_contradiction_triggered"]
    assert scored.loc[0, "quality_score"] == 0
    assert scored.loc[0, "suspicious"]


def test_write_report_has_deterministic_metrics_and_reason_order(tmp_path):
    frame = pd.DataFrame({
        "respondent_id": ["clean", "flagged", "tied"],
        "quality_score": [100.0, 25.0, 25.0],
        "suspicious": [False, True, True],
        "flag_reasons": ["", "Straightlining_Error:scale", "Mahalanobis_Outlier"],
        "straightlining_triggered": [False, True, False],
        "logical_contradiction_triggered": [False, False, True],
        "mahalanobis_outlier_triggered": [False, False, True],
    })
    path = tmp_path / "diagnostics.md"

    write_report(frame, path, "respondent_id")
    report = path.read_text(encoding="utf-8")

    assert "- Processed respondents: 3" in report
    assert "- Suspicious respondents: 2" in report
    assert "- Detector-triggered respondents: 2" in report
    assert "- Missing-value respondents: 0" in report
    assert "- Invalid-value respondents: 0" in report
    assert "- Not-scored respondents: 0" in report
    assert "| Straightlining | 1 | 33.33% |" in report
    assert "| Contradiction | 1 | 33.33% |" in report
    assert "| Mahalanobis | 1 | 33.33% |" in report
    assert report.index("| flagged | 25.00 |") < report.index("| tied | 25.00 |")
    assert "Straightlining_Error:scale" in report
    assert "Mahalanobis_Outlier" in report


def test_summary_and_report_separate_detector_and_data_quality_counts(tmp_path, capsys):
    frame = pd.DataFrame({
        "quality_score": [50.0, None, 100.0],
        "suspicious": [False, None, False],
        "flag_reasons": ["Straightlining_Error:scale", "", ""],
        "data_quality": ["Missing_Value", "Invalid_Value", ""],
        "straightlining_triggered": [True, False, False],
        "logical_contradiction_triggered": [False, False, False],
        "mahalanobis_outlier_triggered": [False, False, False],
    })

    print_summary(frame, tmp_path / "scored.csv")
    summary = capsys.readouterr().out
    assert "Suspicious: 0" in summary
    assert "Detector-triggered: 1" in summary
    assert "Missing: 1" in summary
    assert "Invalid: 1" in summary
    assert "Not scored: 1" in summary

    report = tmp_path / "diagnostics.md"
    write_report(frame, report)
    content = report.read_text(encoding="utf-8")
    assert "- Suspicious respondents: 0" in content
    assert "- Detector-triggered respondents: 1" in content
    assert "- Missing-value respondents: 1" in content
    assert "- Invalid-value respondents: 1" in content
    assert "- Not-scored respondents: 1" in content
    assert "- Not-scored reason: no positive-weight detector had enough valid responses" in content


def test_write_report_handles_empty_frame(tmp_path):
    frame = pd.DataFrame({
        "quality_score": pd.Series(dtype=float),
        "suspicious": pd.Series(dtype="boolean"),
        "flag_reasons": pd.Series(dtype=str),
        "straightlining_triggered": pd.Series(dtype=bool),
        "logical_contradiction_triggered": pd.Series(dtype=bool),
        "mahalanobis_outlier_triggered": pd.Series(dtype=bool),
    })

    path = write_report(frame, tmp_path / "empty.md")

    assert path.read_text(encoding="utf-8").count("N/A") == 4
    assert "| None | N/A | No detector-triggered respondents |" in path.read_text(encoding="utf-8")