"""Run the detector spike evaluation on spike_data.csv."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from surveyguard.config import BlockConfig, PairConfig, RulesConfig
from surveyguard.detectors import logical_contradictions, mahalanobis, straightlining


DATA_PATH = Path(__file__).with_name("spike_data.csv")
MAHALANOBIS_THRESHOLD = 6.0


def build_spike_rules(columns: tuple[str, ...]) -> RulesConfig:
    block = BlockConfig(
        name="extroversion",
        columns=columns,
        minimum=1.0,
        maximum=5.0,
        high_min=4.0,
        low_max=2.0,
        irv_threshold=0.0,
    )
    return RulesConfig(
        blocks={block.name: block},
        inverted_pairs=(
            PairConfig("EXT1", "EXT2", block.name),
            PairConfig("EXT3", "EXT4", block.name),
        ),
        thresholds={"mahalanobis_outlier": MAHALANOBIS_THRESHOLD},
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
    columns = tuple(frame.columns)
    rules = build_spike_rules(columns)

    straightlining_flags = frame.apply(
        lambda row: straightlining(row, rules.blocks).triggered,
        axis=1,
    )
    contradiction_flags = frame.apply(
        lambda row: logical_contradictions(row, rules).triggered,
        axis=1,
    )
    distances, mahalanobis_flags = mahalanobis(
        frame,
        columns,
        MAHALANOBIS_THRESHOLD,
    )

    threshold = exact_five_percent_threshold(distances)

    print(f"Straightlining fals positive rate: {straightlining_flags.mean() * 100:.1f}%")
    print(f"Logical contradiction fals positive rate: {contradiction_flags.mean() * 100:.1f}%")
    print(
        "Mahalanobis fals positive rate "
        f"(threshold={MAHALANOBIS_THRESHOLD:g}): {mahalanobis_flags.mean() * 100:.1f}%"
    )
    print(f"Mahalanobis D^2 threshold for exactly 5%: {threshold:.6f}")


if __name__ == "__main__":
    main()