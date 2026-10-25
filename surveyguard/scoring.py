"""Detector aggregation and scored dataframe creation."""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import ContradictionRule, RulesConfig
from .detectors import DetectorResult, contradiction_matches, mahalanobis, straightlining_irvs
from .errors import MathematicalError
from .io import resolve_rules


@dataclass(frozen=True)
class ScaleRun:
    """Per-scale facts of one run, shared by the report, the CLI, and the web interface."""

    name: str
    module: str | None
    items: int
    detectors: tuple[str, ...]
    threshold: float | None
    threshold_source: str
    valid_rows: int
    required_rows: int
    straightlining_count: int | None
    mahalanobis_count: int | None
    mahalanobis_status: str


@dataclass(frozen=True)
class ScoringRun:
    scored: pd.DataFrame
    scales: tuple[ScaleRun, ...]
    skipped_scales: tuple[str, ...]
    skipped_rules: tuple[ContradictionRule, ...]
    mahalanobis_min_scales: int


def _normalise_questions(frame: pd.DataFrame, rules: RulesConfig) -> pd.DataFrame:
    normalised = frame.copy()
    ranges = [(scale.columns, scale) for scale in rules.scales.values()]
    ranges += [((variable.name,), variable) for variable in rules.variables.values()]
    for columns, bounds in ranges:
        for column in columns:
            values = pd.to_numeric(frame[column], errors="coerce")
            missing = values.isin(bounds.missing_codes)
            out_of_range = values.notna() & (
                (values < bounds.valid_min) | (values > bounds.valid_max)
            )
            normalised[column] = values.mask(missing | out_of_range)
    return normalised


def _data_quality_markers(frame: pd.DataFrame, rules: RulesConfig) -> list[str]:
    """The sorted `data_quality` markers of every row, from the raw question values."""
    missing = np.zeros(len(frame), dtype=bool)
    invalid = np.zeros(len(frame), dtype=bool)
    scales_by_column = {
        column: scale
        for scale in rules.scales.values()
        for column in scale.columns
    }
    for column in rules.question_columns:
        raw = frame[column]
        value = pd.to_numeric(raw, errors="coerce")
        scale = scales_by_column[column]
        blank = raw.isna() | raw.eq("")
        coded = value.isin(scale.missing_codes)
        out_of_range = value.notna() & ~coded & ((value < scale.valid_min) | (value > scale.valid_max))
        missing |= ((value.isna() & blank) | coded).to_numpy(dtype=bool)
        invalid |= ((value.isna() & ~blank) | out_of_range).to_numpy(dtype=bool)
    labels = {
        (False, False): "",
        (True, False): "Invalid_Value",
        (False, True): "Missing_Value",
        (True, True): "Invalid_Value;Missing_Value",
    }
    return [labels[pair] for pair in zip(invalid.tolist(), missing.tolist())]


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
        if not scale.runs_mahalanobis:
            continue
        try:
            distances[scale.name] = mahalanobis(
                frame, scale.columns, scale.mahalanobis_threshold, scale.mahalanobis_min_rows
            )
        except MathematicalError as exc:
            raise MathematicalError(f"Mahalanobis covariance matrix for scale {scale.name!r} is singular") from exc
    return distances


def _scale_runs(
    analysis_frame: pd.DataFrame,
    rules: RulesConfig,
    scale_distances: dict[str, tuple[pd.Series, pd.Series]],
    straightlining_counts: dict[str, int],
) -> tuple[ScaleRun, ...]:
    runs: list[ScaleRun] = []
    for scale in rules.scales.values():
        valid_rows = int(analysis_frame[list(scale.columns)].notna().all(axis=1).sum())
        straightlining_count = None
        if scale.runs_straightlining:
            straightlining_count = straightlining_counts[scale.name]
        mahalanobis_count = None
        status = "-"
        if scale.runs_mahalanobis:
            mahalanobis_count = int(scale_distances[scale.name][1].sum())
            status = (
                "available"
                if valid_rows >= scale.mahalanobis_min_rows
                else f"not available ({valid_rows} valid rows, needs {scale.mahalanobis_min_rows})"
            )
        runs.append(ScaleRun(
            name=scale.name,
            module=scale.module,
            items=len(scale.columns),
            detectors=tuple(
                detector
                for detector, runs_detector in (
                    ("straightlining", scale.runs_straightlining),
                    ("mahalanobis_outlier", scale.runs_mahalanobis),
                )
                if runs_detector
            ),
            threshold=scale.mahalanobis_threshold,
            threshold_source=scale.threshold_source,
            valid_rows=valid_rows,
            required_rows=scale.mahalanobis_min_rows,
            straightlining_count=straightlining_count,
            mahalanobis_count=mahalanobis_count,
            mahalanobis_status=status,
        ))
    return tuple(runs)


def score_run(frame: pd.DataFrame, rules: RulesConfig) -> ScoringRun:
    resolved = resolve_rules(rules, frame.columns)
    active = resolved.rules
    output = frame.copy()
    analysis_frame = _normalise_questions(frame, active)
    scale_distances = _scale_distances(analysis_frame, active)
    # Column-wise detector results as plain lists, so the row loop below never indexes a pandas object.
    straightlining_columns = [
        (name, irvs.tolist(), (irvs <= active.scales[name].irv_threshold).tolist())
        for name, irvs in straightlining_irvs(analysis_frame, active.scales).items()
    ]
    contradiction_columns = [
        (rule.label, evaluable.tolist(), triggered.tolist())
        for rule, (evaluable, triggered) in zip(
            active.contradictions, contradiction_matches(analysis_frame, active.contradictions)
        )
    ]
    distance_columns = [
        (name, scale_distance.tolist(), scale_outliers.tolist())
        for name, (scale_distance, scale_outliers) in scale_distances.items()
    ]
    data_quality = _data_quality_markers(frame, active)
    rows: list[dict[str, object]] = []
    for position in range(len(frame)):
        straightlining_result = DetectorResult("straightlining", available=False)
        scale_irvs: dict[str, float] = {}
        for name, irvs, flags in straightlining_columns:
            if pd.isna(irvs[position]):
                continue
            straightlining_result.available = True
            scale_irvs[name] = irvs[position]
            if flags[position]:
                straightlining_result.triggered = True
                straightlining_result.reasons.append(f"Straightlining_{name}")
        straightlining_result.penalty = 1.0 if straightlining_result.triggered else 0.0
        straightlining_result.details["irv"] = scale_irvs
        contradiction_result = DetectorResult("logical_contradiction", available=False)
        for label, evaluable, triggered in contradiction_columns:
            if not evaluable[position]:
                continue
            contradiction_result.available = True
            if triggered[position]:
                contradiction_result.triggered = True
                contradiction_result.reasons.append(label)
        contradiction_result.penalty = 1.0 if contradiction_result.triggered else 0.0
        results = [straightlining_result, contradiction_result]
        outlier_result = DetectorResult("mahalanobis_outlier", available=False)
        distances: dict[str, float] = {}
        flagged_scales: list[str] = []
        for name, scale_distance, scale_outliers in distance_columns:
            distance = scale_distance[position]
            distances[name] = distance
            if pd.isna(distance):
                continue
            outlier_result.available = True
            if scale_outliers[position]:
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
            "data_quality": data_quality[position],
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
    return ScoringRun(
        scored=scored,
        scales=_scale_runs(
            analysis_frame,
            active,
            scale_distances,
            {name: sum(flags) for name, _, flags in straightlining_columns},
        ),
        skipped_scales=resolved.skipped_scales,
        skipped_rules=resolved.skipped_rules,
        mahalanobis_min_scales=active.mahalanobis_min_scales,
    )


def score_dataframe(frame: pd.DataFrame, rules: RulesConfig) -> pd.DataFrame:
    return score_run(frame, rules).scored
