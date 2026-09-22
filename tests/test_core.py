import json

import numpy as np
import pandas as pd
import pytest

from surveyguard.config import load_rules
from surveyguard.detectors import DetectorResult, irv, logical_contradictions, mahalanobis, straightlining
from surveyguard.errors import ConfigurationError, DataValidationError, MathematicalError
from surveyguard.io import load_csv
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


def test_missing_configured_column_fails_before_scoring(tmp_path):
    rules = load_rules(FIXTURE_RULES)
    csv_path = tmp_path / "missing.csv"
    pd.DataFrame({"respondent_id": ["r1"], "Q1": [1]}).to_csv(csv_path, index=False)
    with pytest.raises(DataValidationError, match="Missing configured question columns"):
        load_csv(csv_path, rules)


def test_irv_and_straightlining():
    rules = load_rules(FIXTURE_RULES)
    row = pd.Series({"Q1": 3, "Q2": 3, "Q3": 3, "Q4": 3})
    assert irv([3, 3, 3, 3]) == 0
    result = straightlining(row, rules.blocks)
    assert result.triggered is True
    assert result.penalty == 1
    assert "Straightlining_Error:attitude_scale" in result.reasons


@pytest.mark.parametrize(
    ("values", "expected"),
    [((4, 5), True), ((1, 2), True), ((3, 4), False)],
)
def test_inverted_pair_bands(values, expected):
    rules = load_rules(FIXTURE_RULES)
    row = pd.Series({"Q1": 3, "Q2": values[0], "Q3": values[1], "Q4": 3})
    assert logical_contradictions(row, rules).triggered is expected


def test_mahalanobis_centroid_is_zero():
    rows = pd.DataFrame({"Q1": [1, 2, 3, 2], "Q2": [3, 5, 4, 4]})
    distances, triggered = mahalanobis(rows, ("Q1", "Q2"), threshold=100)
    assert distances.loc[3] == pytest.approx(0)
    assert not bool(triggered.any())


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


def test_custom_flag_threshold_is_used():
    results = [DetectorResult("straightlining", penalty=0.25)]
    score, suspicious, _ = aggregate_score(results, {"straightlining": 1.0}, flag_threshold=80)
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