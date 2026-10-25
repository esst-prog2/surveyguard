import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat
import pytest

from surveyguard.config import RulesConfig, load_rules
from surveyguard.detectors import (
    DetectorResult,
    contradiction_matches,
    logical_contradictions,
    straightlining,
    straightlining_irvs,
)
from surveyguard.io import load_input, resolve_rules
from surveyguard.scoring import (
    ScaleRun,
    _normalise_questions,
    _scale_distances,
    _scale_runs,
    aggregate_score,
    score_dataframe,
    score_run,
)


ESS_MOCK_CSV = Path("tests/fixtures/ess_mock.csv")
ESS_RULES = Path("config/scale_logic.json")
FIXTURE_RUNS = [
    ("tests/fixtures/ess_mock.csv", "config/scale_logic.json"),
    ("tests/fixtures/ess2_mock.csv", "config/ess2.json"),
    ("tests/fixtures/three_scales.csv", "tests/fixtures/rules/three_scales.json"),
    ("spike_data.csv", "config/spike_logic.json"),
]


def _numeric_ess_mock() -> pd.DataFrame:
    # SPSS numeric columns cannot hold the fixture's "refused" text, so that one cell becomes a valid 6.
    source = pd.read_csv(ESS_MOCK_CSV)
    source["stflife"] = pd.to_numeric(source["stflife"], errors="coerce").fillna(6)
    return source


def _write_labelled_sav(source: pd.DataFrame, path: Path) -> Path:
    pyreadstat.write_sav(
        source,
        path,
        column_labels={column: f"Label of {column}" for column in source.columns},
        variable_value_labels={"trstprl": {0: "No trust at all", 10: "Complete trust", 77: "Refusal"}},
    )
    return path


def _result_columns(scored: pd.DataFrame, source: pd.DataFrame) -> pd.DataFrame:
    return scored[[column for column in scored.columns if column not in source.columns]]


# Input metadata


def test_sav_input_discards_spss_metadata_and_keeps_raw_codes(tmp_path):
    rules = load_rules(ESS_RULES)
    source = _numeric_ess_mock()
    path = _write_labelled_sav(source, tmp_path / "ess.sav")
    assert pd.read_spss(path, convert_categoricals=False).attrs["column_labels"]

    loaded = load_input(path, rules)

    assert loaded.attrs == {}
    assert loaded["trstprl"].tolist() == source["trstprl"].astype(float).tolist()


def test_csv_and_xlsx_inputs_carry_no_metadata(tmp_path):
    rules = load_rules(ESS_RULES)
    xlsx_path = tmp_path / "ess.xlsx"
    pd.read_csv(ESS_MOCK_CSV).to_excel(xlsx_path, index=False)

    assert load_input(ESS_MOCK_CSV, rules).attrs == {}
    assert load_input(xlsx_path, rules).attrs == {}


def test_sav_results_equal_csv_results(tmp_path):
    rules = load_rules(ESS_RULES)
    source = _numeric_ess_mock()
    csv_path = tmp_path / "ess.csv"
    source.to_csv(csv_path, index=False)
    sav_path = _write_labelled_sav(source, tmp_path / "ess.sav")

    from_csv = score_dataframe(load_input(csv_path, rules), rules)
    from_sav = score_dataframe(load_input(sav_path, rules), rules)

    # SPSS stores the item columns as doubles (4.0), so only the appended result columns are compared as text.
    assert _result_columns(from_sav, source).to_csv(index=False) == _result_columns(from_csv, source).to_csv(index=False)
    assert from_sav["idno"].tolist() == from_csv["idno"].tolist()


# Column-wise scoring against the former row-by-row implementation


def _row_reference_data_quality(row: pd.Series, rules: RulesConfig) -> list[str]:
    # Verbatim copy of scoring._data_quality at commit 4a63fd3.
    markers: list[str] = []
    scales_by_column = {
        column: scale
        for scale in rules.scales.values()
        for column in scale.columns
    }
    for column in rules.question_columns:
        raw_value = row[column]
        value = pd.to_numeric(pd.Series([raw_value]), errors="coerce").iloc[0]
        scale = scales_by_column[column]
        if pd.isna(value):
            markers.append(
                "Missing_Value"
                if pd.isna(raw_value) or raw_value == ""
                else "Invalid_Value"
            )
        elif value in scale.missing_codes:
            markers.append("Missing_Value")
        elif value < scale.valid_min or value > scale.valid_max:
            markers.append("Invalid_Value")
    return sorted(set(markers))


def _row_reference_score_run(frame: pd.DataFrame, rules: RulesConfig) -> tuple[pd.DataFrame, tuple[ScaleRun, ...]]:
    # The row loop of scoring.score_run at commit 4a63fd3, copied verbatim; only the per-scale
    # straightlining counts are handed to _scale_runs as the counts the former code derived from the reasons.
    resolved = resolve_rules(rules, frame.columns)
    active = resolved.rules
    output = frame.copy()
    analysis_frame = _normalise_questions(frame, active)
    scale_distances = _scale_distances(analysis_frame, active)
    rows: list[dict[str, object]] = []
    straightlining_reasons: list[list[str]] = []
    for position, (_, row) in enumerate(analysis_frame.iterrows()):
        raw_row = frame.iloc[position]
        results = [straightlining(row, active.scales), logical_contradictions(row, active.contradictions)]
        straightlining_reasons.append(results[0].reasons)
        outlier_result = DetectorResult("mahalanobis_outlier", available=False)
        distances: dict[str, float] = {}
        flagged_scales: list[str] = []
        for name, (scale_distance, scale_outliers) in scale_distances.items():
            distance = scale_distance.iloc[position]
            distances[name] = distance
            if pd.isna(distance):
                continue
            outlier_result.available = True
            if bool(scale_outliers.iloc[position]):
                flagged_scales.append(name)
        # Below mahalanobis_min_scales the scale-level flags only show in the details and distances.
        if len(flagged_scales) >= active.mahalanobis_min_scales:
            outlier_result.triggered = True
            outlier_result.reasons.extend(f"Mahalanobis_{name}" for name in flagged_scales)
        outlier_result.details["distances"] = distances
        if active.mahalanobis_min_scales > 1:
            outlier_result.details["flagged_scales"] = flagged_scales
        outlier_result.penalty = 1.0 if outlier_result.triggered else 0.0
        results.append(outlier_result)
        score, suspicious, reasons = aggregate_score(results, active.weights, active.flag_threshold)
        rows.append({
            "quality_score": score,
            "suspicious": suspicious,
            "flag_reasons": ";".join(reasons),
            "data_quality": ";".join(_row_reference_data_quality(raw_row, active)),
            "straightlining_triggered": results[0].triggered,
            "straightlining_available": results[0].available,
            "logical_contradiction_triggered": results[1].triggered,
            "logical_contradiction_available": results[1].available,
            "mahalanobis_outlier_triggered": outlier_result.triggered,
            "mahalanobis_outlier_available": outlier_result.available,
            **{f"mahalanobis_distance_{name}": distance for name, distance in distances.items()},
            "detector_details": json.dumps(
                {
                    result.name: {"available": result.available, **result.details}
                    for result in results
                },
                default=str,
            ),
        })
    scored = pd.concat([output.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    scored["suspicious"] = pd.array(scored["suspicious"], dtype="boolean")
    counts = {
        scale.name: sum(f"Straightlining_{scale.name}" in reasons for reasons in straightlining_reasons)
        for scale in active.scales.values()
        if scale.runs_straightlining
    }
    return scored, _scale_runs(analysis_frame, active, scale_distances, counts)


def _edge_case_rules(tmp_path) -> RulesConfig:
    path = tmp_path / "edge_rules.json"
    path.write_text(json.dumps({
        "id_column": "id",
        "mahalanobis_min_scales": 2,
        "scales": {
            "S": {
                "columns": ["s1", "s2", "s3", "s4"],
                "valid_min": 1,
                "valid_max": 5,
                "missing_codes": [9],
                "irv_threshold": 0.25,
                "mahalanobis_threshold": 4.0,
            },
            "T": {
                "columns": ["t1", "t2", "t3"],
                "valid_min": 0,
                "valid_max": 10,
                "missing_codes": [77, 88],
                "irv_threshold": 0,
                "mahalanobis_threshold": 3.0,
            },
        },
        "variables": {"v": {"valid_min": 0, "valid_max": 2, "missing_codes": [9]}},
        "contradictions": [
            {"conditions": [{"column": "s1", "op": ">=", "value": 4}, {"column": "t1", "op": "<", "value": 2}]},
            {"conditions": [{"column": "v", "op": "==", "value": 1}, {"column": "s2", "op": ">", "value": 3}]},
            {"conditions": [{"column": "t2", "op": ">", "value": 5}, {"column": "t2", "op": "<", "value": 8}]},
        ],
    }), encoding="utf-8")
    return load_rules(path)


def _edge_case_frame() -> pd.DataFrame:
    # 16 base rows drawn once with numpy seed 2510, then hand-edited edge cases (see the comments).
    rng = np.random.default_rng(2510)
    frame = pd.DataFrame({
        "id": [f"e{number:02d}" for number in range(1, 17)],
        **{column: rng.integers(1, 6, 16) for column in ("s1", "s2", "s3", "s4")},
        **{column: rng.integers(0, 11, 16) for column in ("t1", "t2", "t3")},
        "v": rng.integers(0, 3, 16),
    })
    frame = frame.astype({column: object for column in ("s1", "s2", "s3", "s4", "t1", "t2", "t3", "v")})
    frame.loc[0, "s3"] = "refused"  # unreadable text -> Invalid_Value
    frame.loc[1, "s3"] = ""  # empty string -> Missing_Value
    frame.loc[2, "s3"] = None  # empty cell -> Missing_Value
    frame.loc[3, "s3"] = "5"  # numeric text counts as 5
    frame.loc[4, "s3"] = 11  # out of range -> Invalid_Value
    frame.loc[5, "s3"] = 9  # missing code -> Missing_Value
    frame.loc[6, ["s1", "s2", "s3", "s4"]] = [1, 1, 2, 2]  # IRV exactly 0.25, the threshold
    frame.loc[7, ["s1", "s2", "s3", "s4"]] = [3, 3, 3, 3]  # constant scale
    frame.loc[7, ["t1", "t2", "t3"]] = [4, 4, 4]  # constant on the second scale too
    frame.loc[8, ["s1", "t1"]] = [4, 1]  # rule 1 boundary: s1>=4 holds at 4
    frame.loc[9, ["s1", "t1"]] = [5, 2]  # rule 1: t1<2 fails at 2
    frame.loc[10, ["v", "s2"]] = [1, 4]  # rule 2 on the rule-only variable
    frame.loc[11, ["v", "s2"]] = [9, 5]  # variable missing code skips rule 2
    frame.loc[12, "t2"] = 6  # rule 3 uses t2 twice and holds
    frame.loc[13, "t2"] = 8  # rule 3 fails at the strict bound
    frame.loc[14, ["s1", "s2", "s3", "s4", "t1", "t2", "t3", "v"]] = None  # nothing evaluable
    frame.loc[15, ["s1", "s2", "s3", "s4", "t1", "t2", "t3"]] = [5, 1, 5, 1, 10, 0, 10]  # extreme on both scales
    return frame


def _assert_same_run(frame: pd.DataFrame, rules: RulesConfig) -> pd.DataFrame:
    expected_scored, expected_scales = _row_reference_score_run(frame, rules)
    run = score_run(frame, rules)

    assert run.scored.to_csv(index=False) == expected_scored.to_csv(index=False)
    assert run.scored.dtypes.equals(expected_scored.dtypes)
    assert run.scales == expected_scales
    return run.scored


@pytest.mark.parametrize(("data", "rules_path"), FIXTURE_RUNS)
def test_column_wise_scoring_matches_row_reference_on_fixtures(data, rules_path):
    rules = load_rules(rules_path)

    _assert_same_run(load_input(data, rules), rules)


def test_column_wise_scoring_matches_row_reference_on_edge_cases(tmp_path):
    rules = _edge_case_rules(tmp_path)

    scored = _assert_same_run(_edge_case_frame(), rules).set_index("id")

    # The edge cases really occur, so the comparison above covers them.
    assert scored.loc["e01", "data_quality"] == "Invalid_Value"
    assert scored.loc["e02", "data_quality"] == "Missing_Value"
    assert scored.loc["e05", "data_quality"] == "Invalid_Value"
    assert scored.loc["e06", "data_quality"] == "Missing_Value"
    assert "Straightlining_S" in scored.loc["e07", "flag_reasons"]
    assert scored.loc["e08", "flag_reasons"].startswith("Straightlining_S;Straightlining_T")
    assert "Contradiction: s1>=4 vs t1<2" in scored.loc["e09", "flag_reasons"]
    assert "Contradiction: s1>=4 vs t1<2" not in scored.loc["e10", "flag_reasons"]
    assert "Contradiction: v==1 vs s2>3" in scored.loc["e11", "flag_reasons"]
    assert "Contradiction: t2>5 vs t2<8" in scored.loc["e13", "flag_reasons"]
    assert "Contradiction: t2>5 vs t2<8" not in scored.loc["e14", "flag_reasons"]
    assert pd.isna(scored.loc["e15", "quality_score"])
    assert scored.loc["e16", "flag_reasons"].endswith("Mahalanobis_S;Mahalanobis_T")


def test_frame_detectors_match_row_detectors(tmp_path):
    rules = _edge_case_rules(tmp_path)
    frame = _edge_case_frame()
    analysis = _normalise_questions(frame, resolve_rules(rules, frame.columns).rules)

    irvs = straightlining_irvs(analysis, rules.scales)
    matches = contradiction_matches(analysis, rules.contradictions)

    for position, (_, row) in enumerate(analysis.iterrows()):
        frame_irvs = {name: values.iloc[position] for name, values in irvs.items() if pd.notna(values.iloc[position])}
        assert frame_irvs == straightlining(row, rules.scales).details["irv"]
        row_result = logical_contradictions(row, rules.contradictions)
        frame_reasons = [
            rule.label for rule, (_, triggered) in zip(rules.contradictions, matches) if triggered.iloc[position]
        ]
        assert frame_reasons == row_result.reasons
        assert any(evaluable.iloc[position] for evaluable, _ in matches) == row_result.available
