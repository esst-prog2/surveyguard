from pathlib import Path

import pandas as pd

from surveyguard.config import load_rules
from surveyguard.detectors import mahalanobis


ROOT = Path(__file__).resolve().parents[1]


def test_mahalanobis_flags_exactly_fifty_spike_respondents():
    responses = pd.read_csv(ROOT / "spike_data.csv")
    rules = load_rules(ROOT / "config" / "scale_logic.json")
    columns = ("EXT1", "EXT2", "EXT3", "EXT4")

    _, flagged = mahalanobis(
        responses,
        columns,
        threshold=rules.thresholds["mahalanobis_outlier"],
    )

    assert len(responses) == 1000
    assert int(flagged.sum()) == 50