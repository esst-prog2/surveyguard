"""Stable CLI summary and Markdown report formatting."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .errors import DataValidationError


def _format_metric(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


def _escape_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def print_summary(frame: pd.DataFrame, output_path: Path) -> None:
    print(f"Processed: {len(frame)}")
    print(f"Suspicious: {int(frame['suspicious'].sum())}")
    print(f"Straightlining: {int(frame['straightlining_triggered'].sum())}")
    print(f"Logical contradiction: {int(frame['logical_contradiction_triggered'].sum())}")
    print(f"Mahalanobis outlier: {int(frame['mahalanobis_outlier_triggered'].sum())}")
    print(f"Missing/invalid: {int(frame['data_quality'].ne('').sum())}")
    print(f"Not scored: {int(frame['quality_score'].isna().sum())}")
    print(f"Average quality score: {frame['quality_score'].mean():.2f}")
    print(f"Minimum quality score: {frame['quality_score'].min():.2f}")
    print(f"Output: {output_path}")


def write_report(frame: pd.DataFrame, report_path: str | Path, id_column: str | None = None) -> Path:
    target = Path(report_path)
    processed = len(frame)
    suspicious = int(frame["suspicious"].fillna(False).sum())
    scored = frame["quality_score"].dropna()
    denominator = processed or 1
    detectors = (
        ("Straightlining", "straightlining_triggered"),
        ("Contradiction", "logical_contradiction_triggered"),
        ("Mahalanobis", "mahalanobis_outlier_triggered"),
    )

    lines = [
        "# SurveyGuard diagnostic report",
        "",
        "## Overview",
        "",
        f"- Processed respondents: {processed}",
        f"- Suspicious respondents: {suspicious}",
        f"- Average quality score: {_format_metric(float(scored.mean()) if not scored.empty else None)}",
        f"- Minimum quality score: {_format_metric(float(scored.min()) if not scored.empty else None)}",
        "",
        "## Detector results",
        "",
        "| Detector | Triggered | Percentage |",
        "| --- | ---: | ---: |",
    ]
    for name, column in detectors:
        count = int(frame[column].fillna(False).sum())
        lines.append(f"| {name} | {count} | {count / denominator * 100:.2f}% |")

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
    lines.extend([
        "",
        "## Flagged respondents",
        "",
        "| Respondent | Quality score | Reasons |",
        "| --- | ---: | --- |",
    ])
    if flagged.empty:
        lines.append("| None | N/A | No flagged respondents |")
    else:
        for index, row in flagged.iterrows():
            respondent = row[id_column] if id_column and id_column in row else index + 1
            score = row["quality_score"]
            score_text = "N/A" if pd.isna(score) else f"{float(score):.2f}"
            lines.append(
                f"| {_escape_cell(respondent)} | {score_text} | "
                f"{_escape_cell(row['flag_reasons'])} |"
            )
    lines.append("")

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(lines), encoding="utf-8")
    except OSError as exc:
        raise DataValidationError(f"Could not write report {target}: {exc}") from exc
    return target