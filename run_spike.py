"""Run the detector spike evaluation on spike_data.csv."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from surveyguard.config import Condition, ContradictionRule, RulesConfig, ScaleConfig
from surveyguard.detectors import logical_contradictions, mahalanobis, straightlining


DATA_PATH = Path(__file__).with_name("spike_data.csv")
MAHALANOBIS_THRESHOLD = 6.0


def _pair_rules(first: str, second: str) -> tuple[ContradictionRule, ContradictionRule]:
    """Express an inverted pair as high-high and low-low contradiction rules on the 1-5 scale."""
    return (
        ContradictionRule((Condition(first, ">=", 4.0), Condition(second, ">=", 4.0))),
        ContradictionRule((Condition(first, "<=", 2.0), Condition(second, "<=", 2.0))),
    )


def build_spike_rules(columns: tuple[str, ...]) -> RulesConfig:
    scale = ScaleConfig(
        name="extroversion",
        columns=columns,
        valid_min=1.0,
        valid_max=5.0,
        missing_codes=(),
        irv_threshold=0.0,
        mahalanobis_threshold=MAHALANOBIS_THRESHOLD,
    )
    return RulesConfig(
        scales={scale.name: scale},
        contradictions=_pair_rules("EXT1", "EXT2") + _pair_rules("EXT3", "EXT4"),
    )


def exact_five_percent_threshold(distances: pd.Series) -> float:
    valid = np.sort(distances.dropna().to_numpy(dtype=float))
    target = int(len(valid) * 0.05)
    if target == 0 or target == len(valid):
        raise ValueError("The dataset must contain enough rows for a 5% target.")

    lower = valid[-target - 1]
    upper = valid[-target]
    if lower == upper:
        raise ValueError("Tied Mahalanobis values make an exact 5% threshold impossible.")
    return float((lower + upper) / 2.0)


def main() -> None:
    frame = pd.read_csv(DATA_PATH)
    columns = ("EXT1", "EXT2", "EXT3", "EXT4")
    rules = build_spike_rules(columns)

    straightlining_flags = frame.apply(
        lambda row: straightlining(row, rules.scales).triggered,
        axis=1,
    )
    contradiction_flags = frame.apply(
        lambda row: logical_contradictions(row, rules.contradictions).triggered,
        axis=1,
    )
    distances, mahalanobis_flags = mahalanobis(
        frame,
        columns,
        MAHALANOBIS_THRESHOLD,
    )

    threshold = exact_five_percent_threshold(distances)
    calibrated_flags = distances > threshold

    print(f"Straightlining false positive rate (4 items): {straightlining_flags.mean() * 100:.1f}%")
    print(f"Logical contradiction false positive rate (4 items): {contradiction_flags.mean() * 100:.1f}%")
    print(
        "Mahalanobis false positive rate (4 items, "
        f"legacy threshold={MAHALANOBIS_THRESHOLD:g}): {mahalanobis_flags.mean() * 100:.1f}%"
    )
    print(f"Mahalanobis D^2 threshold for exactly 5% (4 items): {threshold:.6f}")
    print(f"Mahalanobis false positive rate at calibrated threshold: {calibrated_flags.mean() * 100:.1f}%")


if __name__ == "__main__":
    main()