"""Response loading, validation, and output helpers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

import pandas as pd
import pyreadstat

from .config import ContradictionRule, RulesConfig
from .errors import DataValidationError


SUPPORTED_INPUT_EXTENSIONS = (".csv", ".xlsx", ".sav")


@dataclass(frozen=True)
class ResolvedRules:
    """The rules restricted to the scales, variables, and contradiction rules present in an input."""

    rules: RulesConfig
    skipped_scales: tuple[str, ...] = ()
    skipped_variables: tuple[str, ...] = ()
    skipped_rules: tuple[ContradictionRule, ...] = ()


def resolve_rules(rules: RulesConfig, columns: Iterable[str]) -> ResolvedRules:
    present = set(columns)
    if rules.id_column and rules.id_column not in present:
        raise DataValidationError(f"Missing configured id column: {rules.id_column}")
    missing_required: list[str] = []
    partial: list[tuple[str, list[str]]] = []
    active_scales = {}
    skipped_scales: list[str] = []
    for name, scale in rules.scales.items():
        missing = [column for column in scale.columns if column not in present]
        if not missing:
            active_scales[name] = scale
        elif scale.required:
            missing_required.extend(missing)
        elif len(missing) == len(scale.columns):
            skipped_scales.append(name)
        else:
            partial.append((name, missing))
    if missing_required:
        raise DataValidationError(f"Missing configured question columns: {', '.join(sorted(missing_required))}")
    if partial:
        name, missing = partial[0]
        raise DataValidationError(
            f"Optional scale {name!r} is only partly present in the input; missing columns: {', '.join(missing)}"
        )
    missing_variables = [name for name, variable in rules.variables.items() if variable.required and name not in present]
    if missing_variables:
        raise DataValidationError(f"Missing configured variable columns: {', '.join(sorted(missing_variables))}")
    if not active_scales:
        raise DataValidationError("No configured scale is present in the input")
    active_variables = {name: variable for name, variable in rules.variables.items() if name in present}
    skipped_variables = tuple(name for name in rules.variables if name not in present)
    active_columns = {column for scale in active_scales.values() for column in scale.columns} | set(active_variables)
    active_rules = tuple(rule for rule in rules.contradictions if set(rule.columns) <= active_columns)
    skipped_rules = tuple(rule for rule in rules.contradictions if not set(rule.columns) <= active_columns)
    return ResolvedRules(
        replace(rules, scales=active_scales, variables=active_variables, contradictions=active_rules),
        tuple(skipped_scales),
        skipped_variables,
        skipped_rules,
    )


def _whole_number_ids(frame: pd.DataFrame, id_column: str | None) -> pd.DataFrame:
    """SPSS stores every number as a double; show whole-number ids as 1026, not 1026.0."""
    if not id_column or not pd.api.types.is_float_dtype(frame[id_column]):
        return frame
    ids = frame[id_column]
    present = ids.dropna()
    if not (present == present.round()).all():
        return frame
    frame[id_column] = ids.astype("Int64" if ids.isna().any() else "int64")
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
    # pandas deep-copies attrs on every indexing step; read_spss leaves the whole SPSS metadata there.
    frame.attrs = {}
    resolve_rules(rules, frame.columns)
    if extension == ".sav":
        frame = _whole_number_ids(frame, rules.id_column)
    return frame


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