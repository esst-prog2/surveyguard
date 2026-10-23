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


FIXTURE_RULES = "config/scale_logic.json"
FIXTURE_CSV = "tests/fixtures/ess_mock.csv"
TRUST = ["trstprl", "trstlgl", "trstplc", "trstplt", "trstprt"]
SATISFACTION = ["stflife", "stfeco", "stfgov", "stfdem"]


def _rules_data() -> dict:
    return json.loads(Path(FIXTURE_RULES).read_text(encoding="utf-8"))


def _write_rules(tmp_path, data: dict, name: str = "rules.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _respondent(trust, satisfaction, idno="x") -> dict:
    return {"idno": idno, **dict(zip(TRUST, trust)), **dict(zip(SATISFACTION, satisfaction))}


def _scored_fixture() -> pd.DataFrame:
    rules = load_rules(FIXTURE_RULES)
    return score_dataframe(load_input(FIXTURE_CSV, rules), rules)


def _reasons(scored: pd.DataFrame, idno: int) -> str:
    return scored.loc[scored["idno"] == idno, "flag_reasons"].iloc[0]


def test_load_ess_rules():
    rules = load_rules(FIXTURE_RULES)

    assert rules.id_column == "idno"
    assert list(rules.scales) == ["Trust_Institutions", "Satisfaction"]
    trust = rules.scales["Trust_Institutions"]
    assert trust.columns == tuple(TRUST)
    assert (trust.valid_min, trust.valid_max) == (0, 10)
    assert trust.missing_codes == (77, 88, 99)
    assert trust.mahalanobis_threshold == pytest.approx(11.070498)
    assert rules.scales["Satisfaction"].columns == tuple(SATISFACTION)
    assert rules.scales["Satisfaction"].mahalanobis_threshold == pytest.approx(9.487729)
    assert rules.question_columns == tuple(TRUST + SATISFACTION)
    assert [rule.label for rule in rules.contradictions] == [
        "Contradiction: trstplt>8 vs trstprl<2",
        "Contradiction: trstprt>8 vs trstplt<2",
        "Contradiction: stfgov>8 vs stfdem<2",
    ]


def test_contradiction_label_keeps_fractional_values(tmp_path):
    data = _rules_data()
    data["contradictions"] = [{"conditions": [
        {"column": "trstplt", "op": ">=", "value": 8.5},
        {"column": "trstprl", "op": "==", "value": 0},
        {"column": "stfdem", "op": "<=", "value": 1},
    ]}]

    rules = load_rules(_write_rules(tmp_path, data))

    assert rules.contradictions[0].label == "Contradiction: trstplt>=8.5 vs trstprl==0 vs stfdem<=1"


@pytest.mark.parametrize("legacy_key", ["blocks", "inverted_pairs", "thresholds"])
def test_legacy_rules_keys_are_rejected(tmp_path, legacy_key):
    data = _rules_data()
    data[legacy_key] = {}

    with pytest.raises(ConfigurationError, match=f"Legacy rules key '{legacy_key}'.*'scales' and 'contradictions'"):
        load_rules(_write_rules(tmp_path, data))


def test_legacy_rules_file_is_rejected(tmp_path):
    legacy = {
        "blocks": {"x": {"columns": ["Q1", "Q2"], "min": 1, "max": 5}},
        "inverted_pairs": [["Q1", "Q2", "x"]],
        "thresholds": {"mahalanobis_outlier": 6},
    }

    with pytest.raises(ConfigurationError, match="Legacy rules key 'blocks'"):
        load_rules(_write_rules(tmp_path, legacy))


def _break_scale(data: dict, **changes) -> dict:
    scale = data["scales"]["Trust_Institutions"]
    for key, value in changes.items():
        if value is None:
            del scale[key]
        else:
            scale[key] = value
    return data


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"columns": []}, "Trust_Institutions.*invalid columns"),
        ({"valid_min": 10, "valid_max": 0}, "Trust_Institutions.*valid_min less than valid_max"),
        ({"valid_max": None}, "scales.Trust_Institutions.valid_max must be numeric"),
        ({"missing_codes": [77, 5]}, "Trust_Institutions.*missing code 5 lies inside"),
        ({"mahalanobis_threshold": None}, "scales.Trust_Institutions.mahalanobis_threshold must be numeric"),
        ({"mahalanobis_threshold": 0}, "mahalanobis_threshold must be positive"),
    ],
)
def test_invalid_scale_definitions_are_rejected(tmp_path, changes, message):
    data = _break_scale(_rules_data(), **changes)

    with pytest.raises(ConfigurationError, match=message):
        load_rules(_write_rules(tmp_path, data))


def test_invalid_scale_name_and_shared_column_are_rejected(tmp_path):
    data = _rules_data()
    data["scales"]["Bad name"] = data["scales"].pop("Satisfaction")
    with pytest.raises(ConfigurationError, match="Scale name 'Bad name'"):
        load_rules(_write_rules(tmp_path, data))

    data = _rules_data()
    data["scales"]["Satisfaction"]["columns"].append("trstplt")
    with pytest.raises(ConfigurationError, match="Column 'trstplt' belongs to both"):
        load_rules(_write_rules(tmp_path, data))

    data = {"scales": {}}
    with pytest.raises(ConfigurationError, match="at least one scale"):
        load_rules(_write_rules(tmp_path, data))


@pytest.mark.parametrize(
    ("conditions", "message"),
    [
        ([{"column": "trstplt", "op": ">", "value": 8}], r"contradictions\[1\] must contain at least two conditions"),
        (
            [{"column": "trstplt", "op": "!=", "value": 8}, {"column": "trstprl", "op": "<", "value": 2}],
            r"contradictions\[1\]\.conditions\[0\]\.op '!=' must be one of",
        ),
        (
            [{"column": "trstplt", "op": ">", "value": 8}, {"column": "trstprl", "op": "<", "value": "2"}],
            r"contradictions\[1\]\.conditions\[1\]\.value must be numeric",
        ),
        (
            [{"column": "trstplt", "op": ">", "value": 8}, {"column": "agea", "op": "<", "value": 2}],
            r"contradictions\[1\]\.conditions\[1\]\.column 'agea' must belong to a configured scale",
        ),
    ],
)
def test_invalid_contradiction_rules_are_rejected(tmp_path, conditions, message):
    data = _rules_data()
    data["contradictions"] = [data["contradictions"][0], {"conditions": conditions}]

    with pytest.raises(ConfigurationError, match=message):
        load_rules(_write_rules(tmp_path, data))


def test_optional_rule_settings_use_documented_defaults(tmp_path):
    rules_path = _write_rules(tmp_path, {
        "scales": {
            "Trust": {"columns": ["trstprl", "trstplt"], "valid_min": 0, "valid_max": 10, "mahalanobis_threshold": 6},
        },
    })

    rules = load_rules(rules_path)

    assert rules.contradictions == ()
    assert rules.scales["Trust"].irv_threshold == 0
    assert rules.scales["Trust"].missing_codes == ()
    assert rules.weights == {
        "straightlining": 1.0,
        "logical_contradiction": 1.0,
        "mahalanobis_outlier": 1.0,
    }
    assert rules.flag_threshold == 50
    assert rules.id_column is None


def test_without_contradictions_the_detector_is_unavailable(tmp_path):
    data = _rules_data()
    del data["contradictions"]
    rules = load_rules(_write_rules(tmp_path, data))

    scored = score_dataframe(load_input(FIXTURE_CSV, rules), rules)

    assert not scored["logical_contradiction_available"].any()
    assert not scored["flag_reasons"].str.contains("Contradiction").any()


def test_missing_configured_column_fails_before_scoring(tmp_path):
    rules = load_rules(FIXTURE_RULES)
    csv_path = tmp_path / "missing.csv"
    pd.read_csv(FIXTURE_CSV).drop(columns=["stfdem"]).to_csv(csv_path, index=False)
    with pytest.raises(DataValidationError, match="Missing configured question columns: stfdem"):
        load_csv(csv_path, rules)


def test_load_xlsx_and_uppercase_extension(tmp_path):
    rules = load_rules(FIXTURE_RULES)
    path = tmp_path / "ess.XLSX"
    pd.read_csv(FIXTURE_CSV).to_excel(path, index=False)

    loaded = load_input(path, rules)

    assert pd.to_numeric(loaded["trstprl"], errors="coerce").tolist()[:3] == [4, 6, 4]
    assert loaded["idno"].tolist() == list(range(1001, 1034))


def test_load_sav_preserves_numeric_codes_with_value_labels(tmp_path):
    rules = load_rules(FIXTURE_RULES)
    path = tmp_path / "ess.sav"
    source = pd.DataFrame([
        _respondent([0, 5, 5, 5, 5], [5, 5, 5, 5], 1),
        _respondent([10, 5, 5, 5, 5], [5, 5, 5, 5], 2),
        _respondent([77, 5, 5, 5, 5], [5, 5, 5, 5], 3),
    ])
    pyreadstat.write_sav(
        source,
        path,
        variable_value_labels={"trstprl": {0: "No trust at all", 10: "Complete trust", 77: "Refusal"}},
    )

    loaded = load_input(path, rules)

    assert loaded["trstprl"].tolist() == [0.0, 10.0, 77.0]
    assert all(isinstance(value, (int, float)) for value in loaded["trstprl"])
    assert loaded["idno"].tolist() == [1, 2, 3]
    assert loaded["idno"].dtype == "int64"


def test_load_sav_keeps_fractional_or_partly_missing_ids_readable(tmp_path):
    rules = load_rules(FIXTURE_RULES)
    rows = [_respondent([5, 5, 5, 5, 5], [5, 5, 5, 5], idno) for idno in (1026, None)]
    missing_path = tmp_path / "missing_id.sav"
    pyreadstat.write_sav(pd.DataFrame(rows), missing_path)
    fractional_path = tmp_path / "fractional_id.sav"
    pyreadstat.write_sav(pd.DataFrame([{**rows[0], "idno": 1026.5}]), fractional_path)

    missing_ids = load_input(missing_path, rules)["idno"]
    fractional_ids = load_input(fractional_path, rules)["idno"]

    assert str(missing_ids.dtype) == "Int64"
    assert missing_ids.iloc[0] == 1026
    assert pd.isna(missing_ids.iloc[1])
    assert fractional_ids.tolist() == [1026.5]


def test_load_input_rejects_unsupported_extension(tmp_path):
    rules = load_rules(FIXTURE_RULES)
    path = tmp_path / "ess.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(DataValidationError, match="Supported extensions"):
        load_input(path, rules)


def test_irv_and_straightlining_per_scale():
    rules = load_rules(FIXTURE_RULES)
    assert irv([3, 3, 3, 3]) == 0
    # Population variance: ((1-2)^2 + (2-2)^2 + (3-2)^2) / 3 = 2/3.
    assert irv([1, 2, 3]) == pytest.approx(2 / 3)

    trust_only = straightlining(pd.Series(_respondent([5] * 5, [6, 4, 5, 7])), rules.scales)
    assert trust_only.triggered is True
    assert trust_only.penalty == 1
    assert trust_only.reasons == ["Straightlining_Trust_Institutions"]

    both = straightlining(pd.Series(_respondent([3] * 5, [3] * 4)), rules.scales)
    assert both.reasons == ["Straightlining_Trust_Institutions", "Straightlining_Satisfaction"]
    assert both.penalty == 1

    varied = straightlining(pd.Series(_respondent([4, 6, 5, 3, 5], [6, 4, 5, 7])), rules.scales)
    assert varied.triggered is False
    assert varied.available is True
    assert varied.reasons == []


def test_straightlining_skips_incomplete_scale():
    rules = load_rules(FIXTURE_RULES)
    row = pd.Series(_respondent([5, None, 5, 5, 5], [7, 7, 7, 7]))

    result = straightlining(row, rules.scales)

    assert result.available is True
    assert result.reasons == ["Straightlining_Satisfaction"]
    assert set(result.details["irv"]) == {"Satisfaction"}


@pytest.mark.parametrize(
    ("trstplt", "trstprl", "expected"),
    [(9, 1, True), (10, 0, True), (8, 1, False), (9, 2, False), (5, 5, False)],
)
def test_explicit_contradiction_rule(trstplt, trstprl, expected):
    rules = load_rules(FIXTURE_RULES)
    row = pd.Series(_respondent([trstprl, 4, 5, trstplt, 6], [6, 5, 6, 7]))

    result = logical_contradictions(row, rules.contradictions)

    assert result.available is True
    assert result.triggered is expected
    assert result.penalty == (1.0 if expected else 0.0)
    assert result.reasons == (["Contradiction: trstplt>8 vs trstprl<2"] if expected else [])


def test_several_contradictions_keep_rule_order():
    rules = load_rules(FIXTURE_RULES)
    row = pd.Series(_respondent([1, 4, 5, 9, 6], [6, 5, 9, 1]))

    result = logical_contradictions(row, rules.contradictions)

    assert result.reasons == [
        "Contradiction: trstplt>8 vs trstprl<2",
        "Contradiction: stfgov>8 vs stfdem<2",
    ]


def test_contradiction_rule_with_missing_value_is_skipped():
    rules = load_rules(FIXTURE_RULES)
    row = pd.Series(_respondent([None, 4, 5, 9, None], [6, 5, 6, None]))

    result = logical_contradictions(row, rules.contradictions)

    assert result.available is False
    assert result.reasons == []


def test_mahalanobis_centroid_is_zero():
    rows = pd.DataFrame({"trstprl": [1, 2, 3, 2], "trstplt": [3, 5, 4, 4]})
    distances, triggered = mahalanobis(rows, ("trstprl", "trstplt"), threshold=100)
    assert distances.loc[3] == pytest.approx(0)
    assert not bool(triggered.any())


def test_mahalanobis_matches_hand_calculated_squared_distances():
    rows = pd.DataFrame({
        "stfgov": [0, 2, 0, 2, 1],
        "stfdem": [0, 0, 2, 2, 1],
    })

    distances, triggered = mahalanobis(rows, ("stfgov", "stfdem"), threshold=1.5)

    # The centroid is (1, 1), and sample covariance is the identity matrix.
    # Each corner is therefore at squared distance 1^2 + 1^2 = 2; the centroid is 0.
    assert distances.tolist() == pytest.approx([2, 2, 2, 2, 0])
    assert triggered.tolist() == [True, True, True, True, False]
    _, at_threshold = mahalanobis(rows, ("stfgov", "stfdem"), threshold=2)
    assert at_threshold.tolist() == [False, False, False, False, False]


def test_singular_covariance_is_controlled():
    rows = pd.DataFrame({"trstprl": [1, 2, 3], "trstplt": [2, 4, 6]})
    with pytest.raises(MathematicalError, match="singular"):
        mahalanobis(rows, ("trstprl", "trstplt"), threshold=1)


def test_singular_scale_is_named_in_the_error():
    rules = load_rules(FIXTURE_RULES)
    frame = pd.read_csv(FIXTURE_CSV)
    frame["stfdem"] = pd.to_numeric(frame["stflife"], errors="coerce")

    with pytest.raises(MathematicalError, match="scale 'Satisfaction' is singular"):
        score_dataframe(frame, rules)


def test_mahalanobis_runs_per_scale_with_own_rows():
    scored = _scored_fixture()
    by_id = scored.set_index("idno")

    assert {"mahalanobis_distance_Trust_Institutions", "mahalanobis_distance_Satisfaction"}.issubset(scored.columns)
    assert "mahalanobis_distance" not in scored.columns
    # 1027 is an outlier on Satisfaction only.
    assert by_id.loc[1027, "mahalanobis_distance_Satisfaction"] > 9.487729
    assert by_id.loc[1027, "mahalanobis_distance_Trust_Institutions"] < 11.070498
    assert "Mahalanobis_Satisfaction" in by_id.loc[1027, "flag_reasons"]
    assert "Mahalanobis_Trust_Institutions" not in by_id.loc[1027, "flag_reasons"]
    # 1028 has a missing trust item: only the Satisfaction distance exists.
    assert pd.isna(by_id.loc[1028, "mahalanobis_distance_Trust_Institutions"])
    assert not pd.isna(by_id.loc[1028, "mahalanobis_distance_Satisfaction"])
    assert by_id.loc[1028, "mahalanobis_outlier_available"]
    details = json.loads(by_id.loc[1028, "detector_details"])
    assert set(details["mahalanobis_outlier"]["distances"]) == {"Trust_Institutions", "Satisfaction"}
    assert by_id.loc[1033, "flag_reasons"] == "Mahalanobis_Trust_Institutions;Mahalanobis_Satisfaction"


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
            reasons=["Contradiction: trstplt>8 vs trstprl<2"],
        ),
        DetectorResult("straightlining", penalty=0.0),
    ]
    score, suspicious, reasons = aggregate_score(
        results,
        {"logical_contradiction": 0.0, "straightlining": 1.0},
    )

    assert score == 100.0
    assert suspicious is False
    assert reasons == ["Contradiction: trstplt>8 vs trstprl<2"]


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


def test_two_straightlining_scales_cost_one_detector_penalty():
    scored = _scored_fixture()
    row = scored.loc[scored["idno"] == 1023].iloc[0]

    assert row["flag_reasons"] == "Straightlining_Trust_Institutions;Straightlining_Satisfaction"
    assert row["quality_score"] == pytest.approx(200 / 3)
    assert round(row["quality_score"], 2) == 66.67
    assert not row["suspicious"]


def test_fixture_rows_receive_designed_reasons():
    scored = _scored_fixture()

    assert _reasons(scored, 1021) == "Straightlining_Trust_Institutions"
    assert _reasons(scored, 1022) == "Straightlining_Satisfaction"
    assert _reasons(scored, 1024) == "Contradiction: trstplt>8 vs trstprl<2"
    assert _reasons(scored, 1025) == ""
    assert _reasons(scored, 1026) == "Contradiction: trstprt>8 vs trstplt<2;Mahalanobis_Trust_Institutions"
    assert _reasons(scored, 1032) == "Straightlining_Satisfaction;Contradiction: trstplt>8 vs trstprl<2"
    assert scored["suspicious"].sum() == 3
    assert scored.loc[scored["suspicious"].fillna(False), "idno"].tolist() == [1026, 1027, 1032]


def test_score_dataframe_preserves_metadata_and_marks_invalid_value():
    rules = load_rules(FIXTURE_RULES)
    frame = load_csv(FIXTURE_CSV, rules)
    scored = score_dataframe(frame, rules)
    assert list(scored["idno"]) == list(frame["idno"])
    assert list(scored["cntry"]) == list(frame["cntry"])
    assert {"quality_score", "suspicious", "flag_reasons", "data_quality"}.issubset(scored.columns)
    by_id = scored.set_index("idno")
    assert by_id.loc[1030, "data_quality"] == "Invalid_Value"
    assert by_id.loc[1030, "trstplc"] == 11
    assert by_id.loc[1031, "data_quality"] == "Invalid_Value"
    assert by_id.loc[1031, "stflife"] == "refused"


def test_score_dataframe_marks_missing_value_without_imputation():
    rules = load_rules(FIXTURE_RULES)
    source = pd.read_csv(FIXTURE_CSV)
    source.loc[0, "trstprl"] = None
    scored = score_dataframe(source, rules)
    assert scored.loc[0, "data_quality"] == "Missing_Value"
    assert pd.isna(scored.loc[0, "trstprl"])
    assert pd.isna(scored.loc[0, "mahalanobis_distance_Trust_Institutions"])
    assert bool(scored.loc[0, "straightlining_available"])
    assert bool(scored.loc[0, "mahalanobis_outlier_available"])
    assert scored.loc[0, "quality_score"] == 100


def test_configured_missing_and_out_of_range_values_are_excluded_from_detectors():
    scored = _scored_fixture()
    by_id = scored.set_index("idno")

    assert len(scored) == 33
    assert by_id.loc[1028, "trstlgl"] == 77
    assert by_id.loc[1028, "data_quality"] == "Missing_Value"
    assert by_id.loc[1029, "stfeco"] == 88
    assert by_id.loc[1029, "stfdem"] == 99
    assert by_id.loc[1029, "data_quality"] == "Missing_Value"
    assert pd.isna(by_id.loc[1029, "mahalanobis_distance_Satisfaction"])
    assert by_id.loc[1029, "straightlining_available"]
    assert pd.isna(by_id.loc[1030, "mahalanobis_distance_Trust_Institutions"])
    details = json.loads(by_id.loc[1028, "detector_details"])
    assert set(details["straightlining"]["irv"]) == {"Satisfaction"}


def test_score_dataframe_returns_unavailable_score_when_no_detector_can_run(capsys):
    rules = load_rules(FIXTURE_RULES)
    source = pd.read_csv(FIXTURE_CSV)
    unscorable = pd.DataFrame([_respondent([None] * 5, [99] * 4, 2001)])
    frame = pd.concat([source, unscorable], ignore_index=True)

    scored = score_dataframe(frame, rules)

    assert pd.isna(scored.iloc[-1]["quality_score"])
    assert pd.isna(scored.iloc[-1]["suspicious"])
    assert not scored.iloc[-1][
        [
            "straightlining_available",
            "logical_contradiction_available",
            "mahalanobis_outlier_available",
        ]
    ].any()
    print_summary(scored, Path("unscored.csv"))
    summary = capsys.readouterr().out
    assert "Not scored: 1" in summary
    assert "Not scored reason: no positive-weight detector had enough valid responses" in summary


def test_score_dataframe_does_not_dilute_available_detector_with_missing_values(tmp_path):
    data = _rules_data()
    data["weights"]["mahalanobis_outlier"] = 0.0
    rules = load_rules(_write_rules(tmp_path, data))
    frame = pd.DataFrame([_respondent([1, None, 5, 9, 6], [6, 5, None, 7], "partial")])

    scored = score_dataframe(frame, rules)

    assert scored.loc[0, "logical_contradiction_available"]
    assert not scored.loc[0, "straightlining_available"]
    assert not scored.loc[0, "mahalanobis_outlier_available"]
    assert scored.loc[0, "logical_contradiction_triggered"]
    assert scored.loc[0, "quality_score"] == 0
    assert scored.loc[0, "suspicious"]


def test_write_report_has_deterministic_metrics_and_reason_order(tmp_path):
    frame = pd.DataFrame({
        "idno": ["clean", "flagged", "tied"],
        "quality_score": [100.0, 25.0, 25.0],
        "suspicious": [False, True, True],
        "flag_reasons": ["", "Straightlining_Trust_Institutions", "Mahalanobis_Satisfaction"],
        "straightlining_triggered": [False, True, False],
        "logical_contradiction_triggered": [False, False, True],
        "mahalanobis_outlier_triggered": [False, False, True],
    })
    path = tmp_path / "diagnostics.md"

    write_report(frame, path, "idno")
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
    assert "Straightlining_Trust_Institutions" in report
    assert "Mahalanobis_Satisfaction" in report


def test_summary_and_report_separate_detector_and_data_quality_counts(tmp_path, capsys):
    frame = pd.DataFrame({
        "quality_score": [50.0, None, 100.0],
        "suspicious": [False, None, False],
        "flag_reasons": ["Straightlining_Satisfaction", "", ""],
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
