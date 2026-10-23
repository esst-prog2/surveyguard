"""Stable CLI summary and Markdown report formatting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .errors import DataValidationError


def _format_metric(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


def _escape_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _data_quality_count(frame: pd.DataFrame, marker: str) -> int:
    if "data_quality" not in frame:
        return 0
    return int(frame["data_quality"].fillna("").str.split(";").map(lambda values: marker in values).sum())


def _detector_trigger_count(frame: pd.DataFrame) -> int:
    detector_columns = [
        "straightlining_triggered",
        "logical_contradiction_triggered",
        "mahalanobis_outlier_triggered",
    ]
    return int(frame[detector_columns].fillna(False).any(axis=1).sum())


def _not_scored_reason(count: int) -> str:
    return (
        "no positive-weight detector had enough valid responses"
        if count
        else "N/A (no not-scored respondents)"
    )


def print_summary(frame: pd.DataFrame, output_path: Path) -> None:
    print(f"Processed: {len(frame)}")
    print(f"Suspicious: {int(frame['suspicious'].sum())}")
    print(f"Detector-triggered: {_detector_trigger_count(frame)}")
    print(f"Straightlining: {int(frame['straightlining_triggered'].sum())}")
    print(f"Logical contradiction: {int(frame['logical_contradiction_triggered'].sum())}")
    print(f"Mahalanobis outlier: {int(frame['mahalanobis_outlier_triggered'].sum())}")
    print(f"Missing: {_data_quality_count(frame, 'Missing_Value')}")
    print(f"Invalid: {_data_quality_count(frame, 'Invalid_Value')}")
    not_scored = int(frame["quality_score"].isna().sum())
    print(f"Not scored: {not_scored}")
    print(f"Not scored reason: {_not_scored_reason(not_scored)}")
    print(f"Average quality score: {frame['quality_score'].mean():.2f}")
    print(f"Minimum quality score: {frame['quality_score'].min():.2f}")
    print(f"Output: {output_path}")


@dataclass(frozen=True)
class ReportOverview:
    processed: int
    suspicious: int
    detector_triggered: int
    missing: int
    invalid: int
    not_scored: int
    average_score: float | None
    minimum_score: float | None


def report_overview(frame: pd.DataFrame) -> ReportOverview:
    scored = frame["quality_score"].dropna()
    return ReportOverview(
        processed=len(frame),
        suspicious=int(frame["suspicious"].fillna(False).sum()),
        detector_triggered=_detector_trigger_count(frame),
        missing=_data_quality_count(frame, "Missing_Value"),
        invalid=_data_quality_count(frame, "Invalid_Value"),
        not_scored=int(frame["quality_score"].isna().sum()),
        average_score=float(scored.mean()) if not scored.empty else None,
        minimum_score=float(scored.min()) if not scored.empty else None,
    )


def detector_results(frame: pd.DataFrame) -> pd.DataFrame:
    """Return detector trigger counts and their percentage of processed respondents."""
    denominator = len(frame) or 1
    detectors = (
        ("Straightlining", "straightlining_triggered"),
        ("Contradiction", "logical_contradiction_triggered"),
        ("Mahalanobis", "mahalanobis_outlier_triggered"),
    )
    counts = [int(frame[column].fillna(False).sum()) for _, column in detectors]
    return pd.DataFrame({
        "Detector": [name for name, _ in detectors],
        "Triggered": counts,
        "Percentage": [count / denominator * 100 for count in counts],
    })


def flagged_respondents(frame: pd.DataFrame, id_column: str | None = None) -> pd.DataFrame:
    """Return suspicious or detector-flagged respondents in report order."""
    flagged = frame.loc[
        frame["suspicious"].fillna(False) | frame["flag_reasons"].fillna("").ne("")
    ].copy()
    flagged["_report_order"] = range(len(flagged))
    flagged["_report_score"] = pd.to_numeric(flagged["quality_score"], errors="coerce")
    flagged = flagged.sort_values(
        ["_report_score", "_report_order"],
        ascending=[True, True],
        na_position="last",
        kind="stable",
    )
    if id_column and id_column in flagged.columns:
        respondents = list(flagged[id_column])
    else:
        respondents = [index + 1 for index in flagged.index]
    return pd.DataFrame({
        "Respondent": pd.Series(respondents, dtype=object),
        "Quality score": pd.Series(list(flagged["_report_score"]), dtype=float),
        "Suspicious": pd.Series(list(flagged["suspicious"].fillna(False)), dtype=bool),
        "Reasons": pd.Series(list(flagged["flag_reasons"]), dtype=object),
    })


def render_report(frame: pd.DataFrame, id_column: str | None = None) -> str:
    overview = report_overview(frame)
    lines = [
        "# SurveyGuard diagnostic report",
        "",
        "## Overview",
        "",
        f"- Processed respondents: {overview.processed}",
        f"- Suspicious respondents: {overview.suspicious}",
        f"- Detector-triggered respondents: {overview.detector_triggered}",
        f"- Missing-value respondents: {overview.missing}",
        f"- Invalid-value respondents: {overview.invalid}",
        f"- Not-scored respondents: {overview.not_scored}",
        f"- Not-scored reason: {_not_scored_reason(overview.not_scored)}",
        f"- Average quality score: {_format_metric(overview.average_score)}",
        f"- Minimum quality score: {_format_metric(overview.minimum_score)}",
        "",
        "## Detector results",
        "",
        "| Detector | Triggered | Percentage |",
        "| --- | ---: | ---: |",
    ]
    for row in detector_results(frame).itertuples(index=False):
        lines.append(f"| {row.Detector} | {row.Triggered} | {row.Percentage:.2f}% |")

    flagged = flagged_respondents(frame, id_column)
    lines.extend([
        "",
        "## Detector-flagged respondents",
        "",
        "| Respondent | Quality score | Reasons |",
        "| --- | ---: | --- |",
    ])
    if flagged.empty:
        lines.append("| None | N/A | No detector-triggered respondents |")
    else:
        for respondent, score, reasons in zip(
            flagged["Respondent"], flagged["Quality score"], flagged["Reasons"]
        ):
            score_text = "N/A" if pd.isna(score) else f"{float(score):.2f}"
            lines.append(f"| {_escape_cell(respondent)} | {score_text} | {_escape_cell(reasons)} |")
    lines.append("")
    return "\n".join(lines)


def write_report(frame: pd.DataFrame, report_path: str | Path, id_column: str | None = None) -> Path:
    target = Path(report_path)
    content = render_report(frame, id_column)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise DataValidationError(f"Could not write report {target}: {exc}") from exc
    return target