"""Stable CLI summary formatting."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def print_summary(frame: pd.DataFrame, output_path: Path) -> None:
    print(f"Processed: {len(frame)}")
    print(f"Suspicious: {int(frame['suspicious'].sum())}")
    print(f"Straightlining: {int(frame['straightlining_triggered'].sum())}")
    print(f"Logical contradiction: {int(frame['logical_contradiction_triggered'].sum())}")
    print(f"Mahalanobis outlier: {int(frame['mahalanobis_outlier_triggered'].sum())}")
    print(f"Missing/invalid: {int(frame['data_quality'].ne('').sum())}")
    print(f"Average quality score: {frame['quality_score'].mean():.2f}")
    print(f"Minimum quality score: {frame['quality_score'].min():.2f}")
    print(f"Output: {output_path}")