"""Detector aggregation and scored dataframe creation."""

from __future__ import annotations

import json

import pandas as pd

from .config import RulesConfig
from .detectors import DetectorResult, logical_contradictions, mahalanobis, straightlining


def _normalise_questions(frame: pd.DataFrame, rules: RulesConfig) -> pd.DataFrame:
    normalised = frame.copy()
    for block in rules.blocks.values():
        for column in block.columns:
            values = pd.to_numeric(frame[column], errors="coerce")
            missing = values.isin(block.missing_values)
            out_of_range = values.notna() & (
                (values < block.minimum) | (values > block.maximum)
            )
            normalised[column] = values.mask(missing | out_of_range)
    return normalised


def _data_quality(row: pd.Series, rules: RulesConfig) -> list[str]:
    markers: list[str] = []
    blocks_by_column = {
        column: block
        for block in rules.blocks.values()
        for column in block.columns
    }
    for column in rules.question_columns:
        raw_value = row[column]
        value = pd.to_numeric(pd.Series([raw_value]), errors="coerce").iloc[0]
        block = blocks_by_column[column]
        if pd.isna(value):
            markers.append(
                "Missing_Value"
                if pd.isna(raw_value) or raw_value == ""
                else "Invalid_Value"
            )
        elif value in block.missing_values:
            markers.append("Missing_Value")
        elif value < block.minimum or value > block.maximum:
            markers.append("Invalid_Value")
    return sorted(set(markers))


def aggregate_score(
    results: list[DetectorResult],
    weights: dict[str, float],
    flag_threshold: float = 50.0,
) -> tuple[float | None, bool | None, list[str]]:
    active = [
        (result, weights.get(result.name, 1.0))
        for result in results
        if result.available and weights.get(result.name, 1.0) > 0
    ]
    reasons = [reason for result in results for reason in result.reasons]
    denominator = sum(weight for _, weight in active)
    if denominator == 0:
        return None, None, reasons
    penalty = sum(result.penalty * weight for result, weight in active) / denominator
    score = max(0.0, min(100.0, 100.0 * (1.0 - penalty)))
    return score, bool(score < flag_threshold), reasons


def score_dataframe(frame: pd.DataFrame, rules: RulesConfig) -> pd.DataFrame:
    output = frame.copy()
    analysis_frame = _normalise_questions(frame, rules)
    question_columns = rules.question_columns
    distances, outliers = mahalanobis(
        analysis_frame,
        question_columns,
        rules.thresholds["mahalanobis_outlier"],
    )
    rows: list[dict[str, object]] = []
    for position, (_, row) in enumerate(analysis_frame.iterrows()):
        raw_row = frame.iloc[position]
        results = [straightlining(row, rules.blocks), logical_contradictions(row, rules)]
        distance = distances.iloc[position]
        outlier_result = DetectorResult(
            "mahalanobis_outlier",
            triggered=bool(outliers.iloc[position]),
            available=not pd.isna(distance),
        )
        if outlier_result.triggered:
            outlier_result.reasons.append("Mahalanobis_Outlier")
        outlier_result.details["distance"] = distance
        outlier_result.penalty = 1.0 if outlier_result.triggered else 0.0
        results.append(outlier_result)
        score, suspicious, reasons = aggregate_score(results, rules.weights, rules.flag_threshold)
        rows.append({
            "quality_score": score,
            "suspicious": suspicious,
            "flag_reasons": ";".join(reasons),
            "data_quality": ";".join(_data_quality(raw_row, rules)),
            "straightlining_triggered": results[0].triggered,
            "straightlining_available": results[0].available,
            "logical_contradiction_triggered": results[1].triggered,
            "logical_contradiction_available": results[1].available,
            "mahalanobis_outlier_triggered": outlier_result.triggered,
            "mahalanobis_outlier_available": outlier_result.available,
            "mahalanobis_distance": distance,
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
    return scored