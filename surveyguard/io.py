"""Response loading, validation, and output helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyreadstat

from .config import RulesConfig
from .errors import DataValidationError


SUPPORTED_INPUT_EXTENSIONS = (".csv", ".xlsx", ".sav")


def _validate_frame(frame: pd.DataFrame, rules: RulesConfig) -> pd.DataFrame:
    missing = sorted(set(rules.question_columns) - set(frame.columns))
    if rules.id_column and rules.id_column not in frame.columns:
        raise DataValidationError(f"Missing configured id column: {rules.id_column}")
    if missing:
        raise DataValidationError(f"Missing configured question columns: {', '.join(missing)}")
    return frame


def load_input(path: str | Path, rules: RulesConfig) -> pd.DataFrame:
    source = Path(path)
    extension = source.suffix.lower()
    if extension not in SUPPORTED_INPUT_EXTENSIONS:
        supported = ", ".join(SUPPORTED_INPUT_EXTENSIONS)
        raise DataValidationError(
            f"Unsupported input extension: {source.suffix or '<none>'}. Supported extensions: {supported}"
        )

    try:
        if extension == ".csv":
            frame = pd.read_csv(source)
        elif extension == ".xlsx":
            frame = pd.read_excel(source, engine="openpyxl")
        else:
            frame = pd.read_spss(source, convert_categoricals=False)
    except (OSError, ValueError, pd.errors.ParserError, pyreadstat.PyreadstatError) as exc:
        raise DataValidationError(f"Could not read input {source}: {exc}") from exc
    return _validate_frame(frame, rules)


def load_csv(path: str | Path, rules: RulesConfig) -> pd.DataFrame:
    """Load a CSV response file for backwards-compatible callers."""
    return load_input(path, rules)


def default_output_path(input_path: str | Path) -> Path:
    source = Path(input_path)
    return source.with_name(f"{source.stem.replace('_raw', '')}_scored.csv")


def write_scored(frame: pd.DataFrame, input_path: str | Path, output_path: str | Path | None = None) -> Path:
    target = Path(output_path) if output_path else default_output_path(input_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(target, index=False)
    return target