"""Command-line application."""

from __future__ import annotations

import argparse

from .config import load_rules
from .errors import SurveyGuardError
from .io import load_csv, write_scored
from .reporting import print_summary
from .scoring import score_dataframe


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Detect suspicious numeric survey response patterns")
    parser.add_argument("input_csv")
    parser.add_argument("--rules", required=True)
    parser.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rules = load_rules(args.rules)
        frame = load_csv(args.input_csv, rules)
        scored = score_dataframe(frame, rules)
        output_path = write_scored(scored, args.input_csv, args.output)
        print_summary(scored, output_path)
    except SurveyGuardError as exc:
        print(f"Error: {exc}")
        return 1
    return 0