"""Schema checks for every bundled rules file in config/, found by glob so new files are covered without edits."""

import json
import re
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd
import pytest

from surveyguard.config import INCLUDABLE_KEYS, SCALE_NAME_PATTERN, load_rules
from surveyguard.io import load_input
from surveyguard.scoring import score_run


CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
ROOT_FILES = sorted(CONFIG_DIR.glob("*.json"))
MODULE_FILES = sorted(path for path in CONFIG_DIR.glob("**/*.json") if path.parent != CONFIG_DIR)
ALL_FILES = ROOT_FILES + MODULE_FILES
ESS_ROOTS = [path for path in ROOT_FILES if re.fullmatch(r"ess\d+\.json", path.name)]


def _name(path: Path) -> str:
    return path.relative_to(CONFIG_DIR).as_posix()


def _raw(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _included_by(path: Path) -> set[Path]:
    """Every file reachable through include lists from path, path itself excluded."""
    reached: set[Path] = set()
    pending = [path]
    while pending:
        current = pending.pop()
        for entry in _raw(current).get("include", []):
            target = (current.parent / entry).resolve()
            if target not in reached:
                reached.add(target)
                pending.append(target)
    return reached


@pytest.mark.parametrize("path", ROOT_FILES, ids=_name)
def test_root_rules_file_loads(path):
    load_rules(path)


@pytest.mark.parametrize("path", ALL_FILES, ids=_name)
def test_include_paths_are_relative_and_exist_inside_config(path):
    for entry in _raw(path).get("include", []):
        assert "\\" not in entry and not PurePosixPath(entry).is_absolute(), f"{_name(path)}: include {entry!r} is not a relative POSIX path"
        target = (path.parent / entry).resolve()
        assert target.is_relative_to(CONFIG_DIR), f"{_name(path)}: include {entry!r} leaves config/"
        assert target.is_file(), f"{_name(path)}: include {entry!r} does not exist"


@pytest.mark.parametrize("path", ALL_FILES, ids=_name)
def test_scale_names_match_the_pattern(path):
    for name in _raw(path).get("scales", {}):
        assert SCALE_NAME_PATTERN.match(name), f"{_name(path)}: scale name {name!r} may only contain letters, digits, and underscores"


@pytest.mark.parametrize("path", MODULE_FILES, ids=_name)
def test_module_files_hold_only_includable_keys(path):
    extra = sorted(set(_raw(path)) - set(INCLUDABLE_KEYS))
    assert not extra, f"{_name(path)}: keys {extra} may only be set in a root rules file"


def test_every_module_file_is_included_by_a_root_file():
    reachable = set().union(*(_included_by(path) for path in ROOT_FILES))
    orphans = [_name(path) for path in MODULE_FILES if path.resolve() not in reachable]
    assert not orphans, f"module files included by no root rules file: {orphans}"


@pytest.mark.parametrize("path", ESS_ROOTS, ids=_name)
def test_ess_round_key_matches_the_file_name(path):
    assert load_rules(path).essround == int(re.search(r"\d+", path.name).group())


def _synthetic_frame(rules, seed: int) -> pd.DataFrame:
    """Every configured column with in-range whole numbers, plus idno and essround."""
    generator = np.random.default_rng(seed)
    rows = 60
    ranges = {column: (scale.valid_min, scale.valid_max) for scale in rules.scales.values() for column in scale.columns}
    ranges.update({name: (variable.valid_min, variable.valid_max) for name, variable in rules.variables.items()})
    frame = pd.DataFrame({
        column: generator.integers(int(low), int(high) + 1, size=rows) for column, (low, high) in ranges.items()
    })
    frame.insert(0, "idno", range(1, rows + 1))
    frame["essround"] = rules.essround
    return frame


@pytest.mark.parametrize("path", ESS_ROOTS, ids=_name)
def test_ess_round_runs_on_synthetic_data_without_skipping_core_scales(tmp_path, path):
    rules = load_rules(path)
    source = tmp_path / "synthetic.csv"
    _synthetic_frame(rules, seed=rules.essround).to_csv(source, index=False)

    run = score_run(load_input(source, rules), rules)

    assert run.skipped_scales == ()
    assert run.skipped_rules == ()
    assert len(run.scored) == 60
    assert {scale.name for scale in rules.scales.values() if scale.module == "core"} <= {item.name for item in run.scales}
