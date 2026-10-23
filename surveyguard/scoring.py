"""Detector aggregation and scored dataframe creation."""

from __future__ import annotations

import json

import pandas as pd

from .config import RulesConfig
from .detectors import DetectorResult, logical_contradictions, mahalanobis, straightlining
from .errors import MathematicalError


def _normalise_questions(frame: pd.DataFrame, rules: RulesConfig) -> pd.DataFrame:
    normalised = frame.copy()
    for scale in rules.scales.values():
        for column in scale.columns:
            values = pd.to_numeric(frame[column], errors="coerce")
            missing = values.isin(scale.missing_codes)
            out_of_range = values.notna() & (
                (values < scale.valid_min) | (values > scale.valid_max)
            )
            normalised[column] = values.mask(missing | out_of_range)
    return normalised


def _data_quality(row: pd.Series, rules: RulesConfig) -> list[str]:
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


def _scale_distances(frame: pd.DataFrame, rules: RulesConfig) -> dict[str, tuple[pd.Series, pd.Series]]:
    distances: dict[str, tuple[pd.Series, pd.Series]] = {}
    for scale in rules.scales.values():
        try:
            distances[scale.name] = mahalanobis(frame, scale.columns, scale.mahalanobis_threshold)
        except MathematicalError as exc:
            raise MathematicalError(f"Mahalanobis covariance matrix for scale {scale.name!r} is singular") from exc
    return distances


def score_dataframe(frame: pd.DataFrame, rules: RulesConfig) -> pd.DataFrame:
    output = frame.copy()
    analysis_frame = _normalise_questions(frame, rules)
    scale_distances = _scale_distances(analysis_frame, rules)
    rows: list[dict[str, object]] = []
    for position, (_, row) in enumerate(analysis_frame.iterrows()):
        raw_row = frame.iloc[position]
        results = [straightlining(row, rules.scales), logical_contradictions(row, rules.contradictions)]
        outlier_result = DetectorResult("mahalanobis_outlier", available=False)
        distances: dict[str, float] = {}
        for name, (scale_distance, scale_outliers) in scale_distances.items():
            distance = scale_distance.iloc[position]
            distances[name] = distance
            if pd.isna(distance):
                continue
            outlier_result.available = True
            if bool(scale_outliers.iloc[position]):
                outlier_result.triggered = True
                outlier_result.reasons.append(f"Mahalanobis_{name}")
        outlier_result.details["distances"] = distances
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
    return scored
