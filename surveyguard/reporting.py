"""Stable CLI summary and Markdown report formatting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

import pandas as pd

from .errors import DataValidationError

if TYPE_CHECKING:
    from .scoring import ScoringRun


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


def print_summary(frame: pd.DataFrame, output_path: Path, skipped_scales: Iterable[str] = ()) -> None:
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
    skipped = list(skipped_scales)
    if skipped:
        print(f"Skipped scales: {', '.join(skipped)}")
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


def scale_results(run: ScoringRun) -> pd.DataFrame:
    """Return one row per evaluated scale; "-" marks a detector that does not run on the scale."""
    def count(value: int | None) -> object:
        return "-" if value is None else value

    return pd.DataFrame({
        "Scale": [scale.name for scale in run.scales],
        "Module": [scale.module or "-" for scale in run.scales],
        "Items": [scale.items for scale in run.scales],
        "Detectors": [", ".join(scale.detectors) for scale in run.scales],
        "Threshold": [
            "-" if scale.threshold is None else f"{scale.threshold:.6f} ({scale.threshold_source})"
            for scale in run.scales
        ],
        "Valid rows": [scale.valid_rows for scale in run.scales],
        "Straightlining": pd.Series([count(scale.straightlining_count) for scale in run.scales], dtype=object),
        "Mahalanobis flags (scale-level)": pd.Series(
            [count(scale.mahalanobis_count) for scale in run.scales], dtype=object
        ),
        "Status": [scale.mahalanobis_status for scale in run.scales],
    })


def mahalanobis_count_note(run: ScoringRun) -> str:
    return f"Mahalanobis counts respondents flagged on at least {run.mahalanobis_min_scales} scale(s)."


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


def render_report(frame: pd.DataFrame, id_column: str | None = None, run: ScoringRun | None = None) -> str:
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
    if run is not None:
        lines.extend(["", mahalanobis_count_note(run)])
        table = scale_results(run)
        lines.extend([
            "",
            "## Scale results",
            "",
            "| " + " | ".join(table.columns) + " |",
            "| --- | --- | ---: | --- | --- | ---: | ---: | ---: | --- |",
        ])
        for values in table.itertuples(index=False):
            lines.append("| " + " | ".join(_escape_cell(value) for value in values) + " |")
        skipped_scales = ", ".join(run.skipped_scales) or "None"
        skipped_rules = "; ".join(rule.label for rule in run.skipped_rules) or "None"
        lines.extend([
            "",
            "## Skipped scales and rules",
            "",
            f"- Skipped scales: {_escape_cell(skipped_scales)}",
            f"- Skipped contradiction rules: {_escape_cell(skipped_rules)}",
        ])

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


def write_report(
    frame: pd.DataFrame,
    report_path: str | Path,
    id_column: str | None = None,
    run: ScoringRun | None = None,
) -> Path:
    target = Path(report_path)
    content = render_report(frame, id_column, run)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise DataValidationError(f"Could not write report {target}: {exc}") from exc
    return target