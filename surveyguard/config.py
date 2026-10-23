"""Rules configuration parsing and validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import ConfigurationError


LEGACY_KEYS = ("blocks", "inverted_pairs", "thresholds")
OPERATORS = (">", ">=", "<", "<=", "==")
SCALE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


@dataclass(frozen=True)
class ScaleConfig:
    name: str
    columns: tuple[str, ...]
    valid_min: float
    valid_max: float
    missing_codes: tuple[float, ...]
    irv_threshold: float
    mahalanobis_threshold: float


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

    @property
    def question_columns(self) -> tuple[str, ...]:
        return tuple(column for scale in self.scales.values() for column in scale.columns)


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{label} must be numeric")
    return float(value)


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
    valid_min = _number(raw.get("valid_min"), f"scales.{name}.valid_min")
    valid_max = _number(raw.get("valid_max"), f"scales.{name}.valid_max")
    if not valid_min < valid_max:
        raise ConfigurationError(f"Scale {name!r} must have valid_min less than valid_max")
    raw_missing_codes = raw.get("missing_codes", [])
    if not isinstance(raw_missing_codes, list):
        raise ConfigurationError(f"scales.{name}.missing_codes must be a list")
    missing_codes = tuple(
        _number(value, f"scales.{name}.missing_codes[{index}]")
        for index, value in enumerate(raw_missing_codes)
    )
    inside = [code for code in missing_codes if valid_min <= code <= valid_max]
    if inside:
        raise ConfigurationError(
            f"Scale {name!r} missing code {inside[0]:g} lies inside its valid range {valid_min:g}..{valid_max:g}"
        )
    irv_threshold = _number(raw.get("irv_threshold", 0), f"scales.{name}.irv_threshold")
    mahalanobis_threshold = _number(raw.get("mahalanobis_threshold"), f"scales.{name}.mahalanobis_threshold")
    if mahalanobis_threshold <= 0:
        raise ConfigurationError(f"scales.{name}.mahalanobis_threshold must be positive")
    return ScaleConfig(name, columns, valid_min, valid_max, missing_codes, irv_threshold, mahalanobis_threshold)


def _parse_rule(index: int, raw: Any, scale_columns: set[str]) -> ContradictionRule:
    label = f"contradictions[{index}]"
    if not isinstance(raw, dict) or not isinstance(raw.get("conditions"), list):
        raise ConfigurationError(f"{label} must define a conditions list")
    if len(raw["conditions"]) < 2:
        raise ConfigurationError(f"{label} must contain at least two conditions")
    conditions: list[Condition] = []
    for position, condition in enumerate(raw["conditions"]):
        condition_label = f"{label}.conditions[{position}]"
        if not isinstance(condition, dict):
            raise ConfigurationError(f"{condition_label} must be an object")
        column = condition.get("column")
        if not isinstance(column, str) or column not in scale_columns:
            raise ConfigurationError(f"{condition_label}.column {column!r} must belong to a configured scale")
        op = condition.get("op")
        if op not in OPERATORS:
            raise ConfigurationError(f"{condition_label}.op {op!r} must be one of {', '.join(OPERATORS)}")
        value = _number(condition.get("value"), f"{condition_label}.value")
        conditions.append(Condition(column, op, value))
    return ContradictionRule(tuple(conditions))


def load_rules(path: str | Path) -> RulesConfig:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Could not read rules JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigurationError("Rules root must be a JSON object")
    for key in LEGACY_KEYS:
        if key in data:
            raise ConfigurationError(
                f"Legacy rules key {key!r} is no longer supported; use 'scales' and 'contradictions'"
            )

    raw_scales = data.get("scales")
    if not isinstance(raw_scales, dict) or not raw_scales:
        raise ConfigurationError("Rules must define at least one scale")
    scales: dict[str, ScaleConfig] = {}
    owners: dict[str, str] = {}
    for name, raw in raw_scales.items():
        scale = _parse_scale(name, raw)
        for column in scale.columns:
            if column in owners:
                raise ConfigurationError(
                    f"Column {column!r} belongs to both scale {owners[column]!r} and scale {name!r}"
                )
            owners[column] = name
        scales[name] = scale

    raw_rules = data.get("contradictions", [])
    if not isinstance(raw_rules, list):
        raise ConfigurationError("contradictions must be a list")
    contradictions = tuple(_parse_rule(index, raw, set(owners)) for index, raw in enumerate(raw_rules))

    weights = data.get("weights", {})
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

    flag_threshold = _number(data.get("flag_threshold", 50), "flag_threshold")
    if not 0 <= flag_threshold <= 100:
        raise ConfigurationError("flag_threshold must be between 0 and 100")
    id_column = data.get("id_column")
    if id_column is not None and not isinstance(id_column, str):
        raise ConfigurationError("id_column must be a string or null")
    return RulesConfig(scales, contradictions, merged_weights, flag_threshold, id_column)
