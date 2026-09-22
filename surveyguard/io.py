"""CSV loading, validation, and output helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import RulesConfig
from .errors import DataValidationError


def load_csv(path: str | Path, rules: RulesConfig) -> pd.DataFrame:
    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.ParserError) as exc:
        raise DataValidationError(f"Could not read CSV: {exc}") from exc
    missing = sorted(set(rules.question_columns) - set(frame.columns))
    if rules.id_column and rules.id_column not in frame.columns:
        raise DataValidationError(f"Missing configured id column: {rules.id_column}")
    if missing:
        raise DataValidationError(f"Missing configured question columns: {', '.join(missing)}")
    return frame


def default_output_path(input_path: str | Path) -> Path:
    source = Path(input_path)
    return source.with_name(f"{source.stem.replace('_raw', '')}_scored.csv")


def write_scored(frame: pd.DataFrame, input_path: str | Path, output_path: str | Path | None = None) -> Path:
    target = Path(output_path) if output_path else default_output_path(input_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(target, index=False)
    return target