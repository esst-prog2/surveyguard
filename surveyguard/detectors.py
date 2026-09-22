"""Pure detector calculations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
import pandas as pd

from .config import BlockConfig, PairConfig, RulesConfig
from .errors import MathematicalError


@dataclass
class DetectorResult:
    name: str
    penalty: float = 0.0
    triggered: bool = False
    reasons: list[str] = field(default_factory=list)
    details: dict[str, object] = field(default_factory=dict)


def irv(values: Iterable[float]) -> float:
    array = np.asarray(list(values), dtype=float)
    return float(np.var(array, ddof=0))


def straightlining(row: pd.Series, blocks: dict[str, BlockConfig]) -> DetectorResult:
    result = DetectorResult("straightlining")
    block_irvs: dict[str, float] = {}
    for block in blocks.values():
        values = pd.to_numeric(row[list(block.columns)], errors="coerce").to_numpy(dtype=float)
        if np.isnan(values).any():
            continue
        value = irv(values)
        block_irvs[block.name] = value
        if value <= block.irv_threshold:
            result.triggered = True
            result.reasons.append(f"Straightlining_Error:{block.name}")
    result.penalty = 1.0 if result.triggered else 0.0
    result.details["irv"] = block_irvs
    return result


def logical_contradictions(row: pd.Series, rules: RulesConfig) -> DetectorResult:
    result = DetectorResult("logical_contradiction")
    for pair in rules.inverted_pairs:
        block = rules.blocks[pair.block]
        first = pd.to_numeric(pd.Series([row[pair.first]]), errors="coerce").iloc[0]
        second = pd.to_numeric(pd.Series([row[pair.second]]), errors="coerce").iloc[0]
        if pd.isna(first) or pd.isna(second):
            continue
        high = first >= block.high_min and second >= block.high_min
        low = first <= block.low_max and second <= block.low_max
        if high or low:
            result.triggered = True
            result.reasons.append(f"Logical_Contradiction:{pair.first}/{pair.second}")
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