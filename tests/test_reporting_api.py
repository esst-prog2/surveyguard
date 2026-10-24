import os

import pandas as pd
import pytest

from surveyguard.config import load_rules
from surveyguard.io import load_input
from surveyguard.reporting import (
    ReportOverview,
    detector_results,
    flagged_respondents,
    render_report,
    report_overview,
    write_report,
)
from surveyguard.scoring import score_dataframe


FIXTURE_RULES = "config/scale_logic.json"
FIXTURE_CSV = "tests/fixtures/ess_mock.csv"


def _scored_fixture() -> pd.DataFrame:
    rules = load_rules(FIXTURE_RULES)
    return score_dataframe(load_input(FIXTURE_CSV, rules), rules)


def _flagged_frame() -> pd.DataFrame:
    return pd.DataFrame({
        "respondent_id": ["clean", "unscored", "flagged", "tied", "borderline"],
        "quality_score": [100.0, None, 25.0, 25.0, 50.0],
        "suspicious": pd.array([False, None, True, True, False], dtype="boolean"),
        "flag_reasons": [
            "",
            "Mahalanobis_Trust_Institutions",
            "Straightlining_Satisfaction",
            "A|B",
            "Contradiction: trstplt>8 vs trstprl<2",
        ],
        "data_quality": ["", "Invalid_Value", "", "Missing_Value", ""],
        "straightlining_triggered": [False, False, True, False, False],
        "logical_contradiction_triggered": [False, False, False, True, True],
        "mahalanobis_outlier_triggered": [False, True, False, True, False],
    })


def test_render_report_matches_written_report(tmp_path):
    for frame, id_column in ((_scored_fixture(), "idno"), (_flagged_frame(), None)):
        path = write_report(frame, tmp_path / "diagnostics.md", id_column)
        # write_text applies the platform line ending, so compare decoded text.
        with path.open(encoding="utf-8", newline="") as handle:
            written = handle.read()
        assert written.replace(os.linesep, "\n") == render_report(frame, id_column)


def test_report_overview_values():
    assert report_overview(_scored_fixture()) == ReportOverview(
        processed=33,
        suspicious=3,
        detector_triggered=9,
        missing=2,
        invalid=2,
        not_scored=0,
        # 24 clean rows at 100, six at 200/3 (one detector), three at 100/3 (two detectors).
        average_score=pytest.approx(2900 / 33),
        minimum_score=pytest.approx(100 / 3),
    )
    overview = report_overview(_flagged_frame())
    assert (overview.processed, overview.suspicious, overview.detector_triggered) == (5, 2, 4)
    assert (overview.missing, overview.invalid, overview.not_scored) == (1, 1, 1)
    assert overview.average_score == 50.0
    assert overview.minimum_score == 25.0


def test_report_overview_without_scored_respondents():
    frame = pd.DataFrame({
        "quality_score": pd.Series(dtype=float),
        "suspicious": pd.Series(dtype="boolean"),
        "flag_reasons": pd.Series(dtype=str),
        "straightlining_triggered": pd.Series(dtype=bool),
        "logical_contradiction_triggered": pd.Series(dtype=bool),
        "mahalanobis_outlier_triggered": pd.Series(dtype=bool),
    })

    overview = report_overview(frame)

    assert overview.processed == 0
    assert overview.average_score is None
    assert overview.minimum_score is None
    assert detector_results(frame)["Triggered"].tolist() == [0, 0, 0]
    assert detector_results(frame)["Percentage"].tolist() == [0.0, 0.0, 0.0]
    assert flagged_respondents(frame).empty
    assert "- Average quality score: N/A" in render_report(frame)


def test_detector_results_match_report_table():
    frame = _flagged_frame()
    detectors = detector_results(frame)

    assert detectors.columns.tolist() == ["Detector", "Triggered", "Percentage"]
    assert detectors["Detector"].tolist() == ["Straightlining", "Contradiction", "Mahalanobis"]
    assert detectors["Triggered"].tolist() == [1, 2, 2]
    assert detectors["Percentage"].tolist() == [20.0, 40.0, 40.0]
    report = render_report(frame)
    assert "| Straightlining | 1 | 20.00% |" in report
    assert "| Contradiction | 2 | 40.00% |" in report
    assert "| Mahalanobis | 2 | 40.00% |" in report


def test_flagged_respondents_use_report_order_and_identifiers():
    frame = _flagged_frame()

    flagged = flagged_respondents(frame, "respondent_id")

    assert flagged.columns.tolist() == ["Respondent", "Quality score", "Suspicious", "Reasons"]
    assert flagged["Respondent"].tolist() == ["flagged", "tied", "borderline", "unscored"]
    assert flagged["Suspicious"].tolist() == [True, True, False, False]
    assert flagged["Reasons"].tolist() == [
        "Straightlining_Satisfaction",
        "A|B",
        "Contradiction: trstplt>8 vs trstprl<2",
        "Mahalanobis_Trust_Institutions",
    ]
    assert pd.isna(flagged["Quality score"].iloc[-1])
    report = render_report(frame, "respondent_id")
    positions = [report.index(f"| {name} |") for name in ("flagged", "tied", "borderline", "unscored")]
    assert positions == sorted(positions)
    assert "| tied | 25.00 | A\\|B |" in report

    assert flagged_respondents(frame)["Respondent"].tolist() == [3, 4, 5, 2]
