"""Pure detector calculations."""

from __future__ import annotations

import operator
from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
import pandas as pd

from .config import ContradictionRule, ScaleConfig
from .errors import MathematicalError


@dataclass
class DetectorResult:
    name: str
    penalty: float = 0.0
    triggered: bool = False
    reasons: list[str] = field(default_factory=list)
    details: dict[str, object] = field(default_factory=dict)
    available: bool = True


def irv(values: Iterable[float]) -> float:
    array = np.asarray(list(values), dtype=float)
    return float(np.var(array, ddof=0))


def straightlining(row: pd.Series, scales: dict[str, ScaleConfig]) -> DetectorResult:
    result = DetectorResult("straightlining", available=False)
    scale_irvs: dict[str, float] = {}
    for scale in scales.values():
        values = pd.to_numeric(row[list(scale.columns)], errors="coerce").to_numpy(dtype=float)
        if np.isnan(values).any():
            continue
        result.available = True
        value = irv(values)
        scale_irvs[scale.name] = value
        if value <= scale.irv_threshold:
            result.triggered = True
            result.reasons.append(f"Straightlining_{scale.name}")
    result.penalty = 1.0 if result.triggered else 0.0
    result.details["irv"] = scale_irvs
    return result


_COMPARISONS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
}


def logical_contradictions(row: pd.Series, rules: Iterable[ContradictionRule]) -> DetectorResult:
    result = DetectorResult("logical_contradiction", available=False)
    for rule in rules:
        values = pd.to_numeric(row[list(rule.columns)], errors="coerce")
        if values.isna().any():
            continue
        result.available = True
        if all(
            _COMPARISONS[condition.op](values.iloc[index], condition.value)
            for index, condition in enumerate(rule.conditions)
        ):
            result.triggered = True
            result.reasons.append(rule.label)
    result.penalty = 1.0 if result.triggered else 0.0
    return result


def mahalanobis(rows: pd.DataFrame, columns: tuple[str, ...], threshold: float) -> tuple[pd.Series, pd.Series]:
    values = rows.loc[:, list(columns)].apply(pd.to_numeric, errors="coerce")
    valid = ~values.isna().any(axis=1)
    valid_values = values.loc[valid]
    if len(valid_values) < 2:
        return pd.Series(np.nan, index=rows.index), pd.Series(False, index=rows.index)
    matrix = valid_values.to_numpy(dtype=float)
    centroid = matrix.mean(axis=0)
    covariance = np.cov(matrix, rowvar=False)
    covariance = np.atleast_2d(covariance)
    try:
        inverse = np.linalg.inv(covariance)
    except np.linalg.LinAlgError as exc:
        raise MathematicalError("Mahalanobis covariance matrix is singular") from exc
    deltas = matrix - centroid
    distances = np.einsum("ij,jk,ik->i", deltas, inverse, deltas)
    distance_series = pd.Series(np.nan, index=rows.index, dtype=float)
    distance_series.loc[valid] = distances
    triggered = distance_series > threshold
    return distance_series, triggered.fillna(False)