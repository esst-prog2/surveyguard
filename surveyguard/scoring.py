"""Detector aggregation and scored dataframe creation."""

from __future__ import annotations

import json

import pandas as pd

from .config import RulesConfig
from .detectors import DetectorResult, logical_contradictions, mahalanobis, straightlining


def aggregate_score(
    results: list[DetectorResult],
    weights: dict[str, float],
    flag_threshold: float = 50.0,
) -> tuple[float, bool, list[str]]:
    active = [(result, weights.get(result.name, 1.0)) for result in results if weights.get(result.name, 1.0) > 0]
    denominator = sum(weight for _, weight in active)
    penalty = sum(result.penalty * weight for result, weight in active) / denominator
    score = max(0.0, min(100.0, 100.0 * (1.0 - penalty)))
    reasons = [reason for result in results for reason in result.reasons]
    return score, bool(score < flag_threshold), reasons


def score_dataframe(frame: pd.DataFrame, rules: RulesConfig) -> pd.DataFrame:
    output = frame.copy()
    question_columns = rules.question_columns
    distances, outliers = mahalanobis(frame, question_columns, rules.thresholds.get("mahalanobis_outlier", 0.0))
    rows: list[dict[str, object]] = []
    for index, row in frame.iterrows():
        results = [straightlining(row, rules.blocks), logical_contradictions(row, rules)]
        outlier_result = DetectorResult("mahalanobis_outlier", float(outliers.loc[index]), bool(outliers.loc[index]))
        if outlier_result.triggered:
            outlier_result.reasons.append("Mahalanobis_Outlier")
        outlier_result.details["distance"] = distances.loc[index]
        outlier_result.penalty = 1.0 if outlier_result.triggered else 0.0
        results.append(outlier_result)
        score, _, reasons = aggregate_score(results, rules.weights, rules.flag_threshold)
        data_quality = []
        for column in question_columns:
            value = pd.to_numeric(pd.Series([row[column]]), errors="coerce").iloc[0]
            if pd.isna(value):
                data_quality.append("Missing_Value" if pd.isna(row[column]) or row[column] == "" else "Invalid_Value")
        rows.append({
            "quality_score": score,
            "suspicious": score < rules.flag_threshold,
            "flag_reasons": ";".join(reasons),
            "data_quality": ";".join(sorted(set(data_quality))),
            "straightlining_triggered": results[0].triggered,
            "logical_contradiction_triggered": results[1].triggered,
            "mahalanobis_outlier_triggered": outlier_result.triggered,
            "mahalanobis_distance": outlier_result.details["distance"],
            "detector_details": json.dumps({result.name: result.details for result in results}, default=str),
        })
    return pd.concat([output.reset_index(drop=True), pd.DataFrame(rows)], axis=1)