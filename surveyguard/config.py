"""Rules configuration parsing and validation."""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scipy.stats import chi2

from .errors import ConfigurationError


LEGACY_KEYS = ("blocks", "inverted_pairs", "thresholds")
ROOT_ONLY_KEYS = ("weights", "flag_threshold", "mahalanobis_min_scales", "id_column", "essround")
INCLUDABLE_KEYS = ("include", "scales", "variables", "contradictions")
SCALE_DETECTORS = ("straightlining", "mahalanobis_outlier")
OPERATORS = (">", ">=", "<", "<=", "==")
SCALE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")
UPLOADED_INCLUDE_MESSAGE = (
    "include is not supported for uploaded rules files; choose a bundled rules file or use the command-line tool"
)


@dataclass(frozen=True)
class ScaleConfig:
    name: str
    columns: tuple[str, ...]
    valid_min: float
    valid_max: float
    missing_codes: tuple[float, ...]
    irv_threshold: float
    mahalanobis_threshold: float | None
    module: str | None = None
    required: bool = True
    detectors: tuple[str, ...] = SCALE_DETECTORS
    min_items_straightlining: int | None = None
    mahalanobis_min_rows_per_item: float = 0.0
    threshold_source: str = "configured"

    @property
    def runs_straightlining(self) -> bool:
        return "straightlining" in self.detectors and (
            self.min_items_straightlining is None or len(self.columns) >= self.min_items_straightlining
        )

    @property
    def runs_mahalanobis(self) -> bool:
        return "mahalanobis_outlier" in self.detectors

    @property
    def mahalanobis_min_rows(self) -> int:
        return max(2, math.ceil(self.mahalanobis_min_rows_per_item * len(self.columns)))


@dataclass(frozen=True)
class VariableConfig:
    """A rule-only column: validated and masked like a scale item, but never used by a detector."""

    name: str
    valid_min: float
    valid_max: float
    missing_codes: tuple[float, ...] = ()
    module: str | None = None
    required: bool = True


@dataclass(frozen=True)
class Condition:
    column: str
    op: str
    value: float

    @property
    def label(self) -> str:
        return f"{self.column}{self.op}{self.value:g}"


@dataclass(frozen=True)
class ContradictionRule:
    conditions: tuple[Condition, ...]

    @property
    def columns(self) -> tuple[str, ...]:
        return tuple(condition.column for condition in self.conditions)

    @property
    def label(self) -> str:
        return "Contradiction: " + " vs ".join(condition.label for condition in self.conditions)


@dataclass(frozen=True)
class RulesConfig:
    scales: dict[str, ScaleConfig]
    contradictions: tuple[ContradictionRule, ...] = ()
    weights: dict[str, float] = field(default_factory=lambda: {
        "straightlining": 1.0,
        "logical_contradiction": 1.0,
        "mahalanobis_outlier": 1.0,
    })
    flag_threshold: float = 50.0
    id_column: str | None = None
    variables: dict[str, VariableConfig] = field(default_factory=dict)
    mahalanobis_min_scales: int = 1
    essround: int | None = None

    @property
    def question_columns(self) -> tuple[str, ...]:
        return tuple(column for scale in self.scales.values() for column in scale.columns)


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{label} must be numeric")
    return float(value)


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ConfigurationError(f"{label} must be a positive integer")
    return value


def _range_and_codes(raw: dict, label: str, owner: str) -> tuple[float, float, tuple[float, ...]]:
    valid_min = _number(raw.get("valid_min"), f"{label}.valid_min")
    valid_max = _number(raw.get("valid_max"), f"{label}.valid_max")
    if not valid_min < valid_max:
        raise ConfigurationError(f"{owner} must have valid_min less than valid_max")
    raw_missing_codes = raw.get("missing_codes", [])
    if not isinstance(raw_missing_codes, list):
        raise ConfigurationError(f"{label}.missing_codes must be a list")
    missing_codes = tuple(
        _number(value, f"{label}.missing_codes[{index}]")
        for index, value in enumerate(raw_missing_codes)
    )
    inside = [code for code in missing_codes if valid_min <= code <= valid_max]
    if inside:
        raise ConfigurationError(
            f"{owner} missing code {inside[0]:g} lies inside its valid range {valid_min:g}..{valid_max:g}"
        )
    return valid_min, valid_max, missing_codes


def _module_and_required(raw: dict, label: str) -> tuple[str | None, bool]:
    module = raw.get("module")
    if module is not None and (not isinstance(module, str) or not module):
        raise ConfigurationError(f"{label}.module must be a non-empty string")
    required = raw.get("required", True)
    if not isinstance(required, bool):
        raise ConfigurationError(f"{label}.required must be true or false")
    return module, required


def _detectors(raw: dict, label: str) -> tuple[str, ...]:
    detectors = raw.get("detectors", list(SCALE_DETECTORS))
    if (
        not isinstance(detectors, list)
        or not detectors
        or len(set(detectors)) != len(detectors)
        or not all(detector in SCALE_DETECTORS for detector in detectors)
    ):
        raise ConfigurationError(
            f"{label}.detectors must be a non-empty list of distinct values from {', '.join(SCALE_DETECTORS)}"
        )
    return tuple(detector for detector in SCALE_DETECTORS if detector in detectors)


def _mahalanobis_threshold(raw: dict, name: str, items: int, runs_mahalanobis: bool) -> tuple[float | None, str]:
    has_threshold = "mahalanobis_threshold" in raw
    has_alpha = "mahalanobis_alpha" in raw
    if not runs_mahalanobis:
        if has_threshold or has_alpha:
            raise ConfigurationError(
                f"Scale {name!r} has no Mahalanobis detector, so it must not define "
                "mahalanobis_threshold or mahalanobis_alpha"
            )
        return None, "configured"
    if has_threshold and has_alpha:
        raise ConfigurationError(
            f"Scale {name!r} defines both mahalanobis_threshold and mahalanobis_alpha; only one of the two may be given"
        )
    if has_alpha:
        alpha = _number(raw["mahalanobis_alpha"], f"scales.{name}.mahalanobis_alpha")
        if not 0 < alpha < 1:
            raise ConfigurationError(f"scales.{name}.mahalanobis_alpha must be between 0 and 1")
        return float(chi2.ppf(1 - alpha, df=items)), f"alpha={alpha:g}"
    if not has_threshold:
        raise ConfigurationError(
            f"scales.{name}.mahalanobis_threshold must be numeric, or define scales.{name}.mahalanobis_alpha"
        )
    threshold = _number(raw["mahalanobis_threshold"], f"scales.{name}.mahalanobis_threshold")
    if threshold <= 0:
        raise ConfigurationError(f"scales.{name}.mahalanobis_threshold must be positive")
    return threshold, "configured"


def _parse_scale(name: Any, raw: Any) -> ScaleConfig:
    if not isinstance(name, str) or not SCALE_NAME_PATTERN.match(name):
        raise ConfigurationError(f"Scale name {name!r} may only contain letters, digits, and underscores")
    if not isinstance(raw, dict) or not isinstance(raw.get("columns"), list):
        raise ConfigurationError(f"Scale {name!r} must define a columns list")
    columns = tuple(raw["columns"])
    if not columns or not all(isinstance(column, str) and column for column in columns):
        raise ConfigurationError(f"Scale {name!r} contains invalid columns")
    if len(set(columns)) != len(columns):
        raise ConfigurationError(f"Scale {name!r} lists a column more than once")
    label = f"scales.{name}"
    valid_min, valid_max, missing_codes = _range_and_codes(raw, label, f"Scale {name!r}")
    irv_threshold = _number(raw.get("irv_threshold", 0), f"{label}.irv_threshold")
    module, required = _module_and_required(raw, label)
    detectors = _detectors(raw, label)
    min_items = raw.get("min_items_straightlining")
    if min_items is not None:
        min_items = _positive_int(min_items, f"{label}.min_items_straightlining")
    min_rows_per_item = _number(raw.get("mahalanobis_min_rows_per_item", 0), f"{label}.mahalanobis_min_rows_per_item")
    if min_rows_per_item < 0:
        raise ConfigurationError(f"{label}.mahalanobis_min_rows_per_item must not be negative")
    threshold, source = _mahalanobis_threshold(raw, name, len(columns), "mahalanobis_outlier" in detectors)
    return ScaleConfig(
        name,
        columns,
        valid_min,
        valid_max,
        missing_codes,
        irv_threshold,
        threshold,
        module=module,
        required=required,
        detectors=detectors,
        min_items_straightlining=min_items,
        mahalanobis_min_rows_per_item=min_rows_per_item,
        threshold_source=source,
    )


def _parse_variable(name: Any, raw: Any) -> VariableConfig:
    if not isinstance(name, str) or not name:
        raise ConfigurationError(f"Variable name {name!r} must be a non-empty string")
    if not isinstance(raw, dict):
        raise ConfigurationError(f"Variable {name!r} must be an object")
    label = f"variables.{name}"
    valid_min, valid_max, missing_codes = _range_and_codes(raw, label, f"Variable {name!r}")
    module, required = _module_and_required(raw, label)
    return VariableConfig(name, valid_min, valid_max, missing_codes, module, required)


def _parse_rule(index: int, raw: Any, rule_columns: set[str], source: str) -> ContradictionRule:
    label = f"contradictions[{index}]"
    where = f" (in {source})"
    if not isinstance(raw, dict) or not isinstance(raw.get("conditions"), list):
        raise ConfigurationError(f"{label} must define a conditions list{where}")
    if len(raw["conditions"]) < 2:
        raise ConfigurationError(f"{label} must contain at least two conditions{where}")
    conditions: list[Condition] = []
    for position, condition in enumerate(raw["conditions"]):
        condition_label = f"{label}.conditions[{position}]"
        if not isinstance(condition, dict):
            raise ConfigurationError(f"{condition_label} must be an object{where}")
        column = condition.get("column")
        if not isinstance(column, str) or column not in rule_columns:
            raise ConfigurationError(
                f"{condition_label}.column {column!r} must belong to a configured scale or be a declared variable{where}"
            )
        op = condition.get("op")
        if op not in OPERATORS:
            raise ConfigurationError(f"{condition_label}.op {op!r} must be one of {', '.join(OPERATORS)}{where}")
        try:
            value = _number(condition.get("value"), f"{condition_label}.value")
        except ConfigurationError as exc:
            raise ConfigurationError(f"{exc}{where}") from exc
        conditions.append(Condition(column, op, value))
    return ContradictionRule(tuple(conditions))


def _display(path: Path, root_dir: Path) -> str:
    try:
        return Path(os.path.relpath(path, root_dir)).as_posix()
    except ValueError:
        return path.as_posix()


def _load_tree(
    path: Path,
    root_dir: Path,
    stack: tuple[Path, ...],
    seen: set[Path],
    allow_include: bool,
) -> list[tuple[str, dict]]:
    """Return (display name, data) for every rules file, included files first, in depth-first list order."""
    resolved = path.resolve()
    name = _display(resolved, root_dir)
    is_root = not stack
    if resolved in stack:
        cycle = [_display(entry, root_dir) for entry in stack[stack.index(resolved):]] + [name]
        raise ConfigurationError(f"Circular include: {' -> '.join(cycle)}")
    if resolved in seen:
        raise ConfigurationError(f"Rules file {name} is included more than once")
    seen.add(resolved)
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        if is_root:
            raise ConfigurationError(f"Could not read rules JSON: {exc}") from exc
        raise ConfigurationError(f"Could not read included rules file {name}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigurationError("Rules root must be a JSON object" if is_root else f"Included rules file {name} must be a JSON object")
    for key in LEGACY_KEYS:
        if key in data:
            raise ConfigurationError(
                f"Legacy rules key {key!r} is no longer supported; use 'scales' and 'contradictions' (in {name})"
            )
    if not is_root:
        for key in data:
            if key in ROOT_ONLY_KEYS:
                raise ConfigurationError(f"{key!r} may only be set in the root rules file, not in included file {name}")
            if key not in INCLUDABLE_KEYS:
                raise ConfigurationError(
                    f"Included rules file {name} may only contain {', '.join(INCLUDABLE_KEYS)}; found {key!r}"
                )
    includes = data.get("include", [])
    if not isinstance(includes, list) or not all(isinstance(entry, str) and entry for entry in includes):
        raise ConfigurationError(f"include must be a list of file paths (in {name})")
    if includes and not allow_include:
        raise ConfigurationError(UPLOADED_INCLUDE_MESSAGE)
    entries: list[tuple[str, dict]] = []
    for entry in includes:
        entries.extend(_load_tree(resolved.parent / entry, root_dir, stack + (resolved,), seen, allow_include))
    entries.append((name, data))
    return entries


def load_rules(path: str | Path, *, allow_include: bool = True) -> RulesConfig:
    root_path = Path(path)
    entries = _load_tree(root_path, root_path.resolve().parent, (), set(), allow_include)
    root = entries[-1][1]

    scales: dict[str, ScaleConfig] = {}
    variables: dict[str, VariableConfig] = {}
    defined_in: dict[str, str] = {}
    owners: dict[str, tuple[str, str]] = {}
    raw_rules: list[tuple[int, Any, str]] = []

    def claim(column: str, owner: str, source: str) -> None:
        if column in owners:
            other, other_source = owners[column]
            where = "" if other_source == source else f" ({other_source})"
            here = "" if other_source == source else f" ({source})"
            raise ConfigurationError(f"Column {column!r} belongs to both {other}{where} and {owner}{here}")
        owners[column] = (owner, source)

    for source, data in entries:
        raw_scales = data.get("scales", {})
        if not isinstance(raw_scales, dict):
            raise ConfigurationError(f"scales must be an object (in {source})")
        for name, raw in raw_scales.items():
            if name in scales:
                raise ConfigurationError(f"Scale {name!r} is defined in both {defined_in['scale:' + name]} and {source}")
            scale = _parse_scale(name, raw)
            for column in scale.columns:
                claim(column, f"scale {name!r}", source)
            scales[name] = scale
            defined_in["scale:" + name] = source
        raw_variables = data.get("variables", {})
        if not isinstance(raw_variables, dict):
            raise ConfigurationError(f"variables must be an object (in {source})")
        for name, raw in raw_variables.items():
            if name in variables:
                raise ConfigurationError(
                    f"Variable {name!r} is defined in both {defined_in['variable:' + name]} and {source}"
                )
            variable = _parse_variable(name, raw)
            claim(name, f"variable {name!r}", source)
            variables[name] = variable
            defined_in["variable:" + name] = source
        file_rules = data.get("contradictions", [])
        if not isinstance(file_rules, list):
            raise ConfigurationError(f"contradictions must be a list (in {source})")
        raw_rules.extend((index, raw, source) for index, raw in enumerate(file_rules))

    if not scales:
        raise ConfigurationError("Rules must define at least one scale")
    contradictions = tuple(_parse_rule(index, raw, set(owners), source) for index, raw, source in raw_rules)

    weights = root.get("weights", {})
    if not isinstance(weights, dict):
        raise ConfigurationError("weights must be an object")
    merged_weights = RulesConfig.__dataclass_fields__["weights"].default_factory()
    for name, value in weights.items():
        parsed = _number(value, f"weights.{name}")
        if parsed < 0:
            raise ConfigurationError(f"weights.{name} must not be negative")
        merged_weights[name] = parsed
    if sum(merged_weights.values()) == 0:
        raise ConfigurationError("At least one detector weight must be positive")

    flag_threshold = _number(root.get("flag_threshold", 50), "flag_threshold")
    if not 0 <= flag_threshold <= 100:
        raise ConfigurationError("flag_threshold must be between 0 and 100")
    mahalanobis_min_scales = _positive_int(root.get("mahalanobis_min_scales", 1), "mahalanobis_min_scales")
    id_column = root.get("id_column")
    if id_column is not None and not isinstance(id_column, str):
        raise ConfigurationError("id_column must be a string or null")
    essround = root.get("essround")
    if essround is not None:
        essround = _positive_int(essround, "essround")
    return RulesConfig(
        scales,
        contradictions,
        merged_weights,
        flag_threshold,
        id_column,
        variables,
        mahalanobis_min_scales,
        essround,
    )
