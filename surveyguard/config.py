"""Rules configuration parsing and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import ConfigurationError


@dataclass(frozen=True)
class BlockConfig:
    name: str
    columns: tuple[str, ...]
    minimum: float
    maximum: float
    high_min: float
    low_max: float
    irv_threshold: float


@dataclass(frozen=True)
class PairConfig:
    first: str
    second: str
    block: str


@dataclass(frozen=True)
class RulesConfig:
    blocks: dict[str, BlockConfig]
    inverted_pairs: tuple[PairConfig, ...]
    weights: dict[str, float] = field(default_factory=lambda: {
        "straightlining": 1.0,
        "logical_contradiction": 1.0,
        "mahalanobis_outlier": 1.0,
    })
    thresholds: dict[str, float] = field(default_factory=dict)
    flag_threshold: float = 50.0
    id_column: str | None = None

    @property
    def question_columns(self) -> tuple[str, ...]:
        return tuple(column for block in self.blocks.values() for column in block.columns)


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{label} must be numeric")
    return float(value)


def load_rules(path: str | Path) -> RulesConfig:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Could not read rules JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigurationError("Rules root must be a JSON object")

    raw_blocks = data.get("blocks")
    if not isinstance(raw_blocks, dict) or not raw_blocks:
        raise ConfigurationError("Rules must define at least one question block")
    blocks: dict[str, BlockConfig] = {}
    for name, raw in raw_blocks.items():
        if not isinstance(raw, dict) or not isinstance(raw.get("columns"), list):
            raise ConfigurationError(f"Block {name!r} must define a columns list")
        columns = tuple(raw["columns"])
        if not columns or not all(isinstance(column, str) and column for column in columns):
            raise ConfigurationError(f"Block {name!r} contains invalid columns")
        minimum = _number(raw.get("min"), f"blocks.{name}.min")
        maximum = _number(raw.get("max"), f"blocks.{name}.max")
        high_min = _number(raw.get("high_min", maximum - 1), f"blocks.{name}.high_min")
        low_max = _number(raw.get("low_max", minimum + 1), f"blocks.{name}.low_max")
        irv_threshold = _number(raw.get("irv_threshold", 0), f"blocks.{name}.irv_threshold")
        if not minimum < maximum or not minimum <= low_max < high_min <= maximum:
            raise ConfigurationError(f"Block {name!r} has invalid scale bands")
        blocks[name] = BlockConfig(name, columns, minimum, maximum, high_min, low_max, irv_threshold)

    raw_pairs = data.get("inverted_pairs", [])
    if not isinstance(raw_pairs, list):
        raise ConfigurationError("inverted_pairs must be a list")
    pairs: list[PairConfig] = []
    for index, raw in enumerate(raw_pairs):
        if not isinstance(raw, list) or len(raw) not in (2, 3):
            raise ConfigurationError(f"inverted_pairs[{index}] must contain two columns and optionally a block")
        first, second = raw[0], raw[1]
        block = raw[2] if len(raw) == 3 else next(
            (block_name for block_name, block_config in blocks.items() if first in block_config.columns and second in block_config.columns),
            None,
        )
        if not isinstance(first, str) or not isinstance(second, str) or not isinstance(block, str):
            raise ConfigurationError(f"inverted_pairs[{index}] references an unknown block")
        if block not in blocks or first not in blocks[block].columns or second not in blocks[block].columns:
            raise ConfigurationError(f"inverted_pairs[{index}] columns must belong to block {block!r}")
        pairs.append(PairConfig(first, second, block))

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

    thresholds = data.get("thresholds", {})
    if not isinstance(thresholds, dict):
        raise ConfigurationError("thresholds must be an object")
    parsed_thresholds = {name: _number(value, f"thresholds.{name}") for name, value in thresholds.items()}
    flag_threshold = _number(data.get("flag_threshold", 50), "flag_threshold")
    if not 0 <= flag_threshold <= 100:
        raise ConfigurationError("flag_threshold must be between 0 and 100")
    id_column = data.get("id_column")
    if id_column is not None and not isinstance(id_column, str):
        raise ConfigurationError("id_column must be a string or null")
    return RulesConfig(blocks, tuple(pairs), merged_weights, parsed_thresholds, flag_threshold, id_column)