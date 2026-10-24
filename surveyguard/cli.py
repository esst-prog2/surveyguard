"""Command-line application."""

from __future__ import annotations

import argparse

from .config import load_rules
from .errors import SurveyGuardError
from .io import load_input, write_scored
from .reporting import print_summary, write_report
from .scoring import score_run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Detect suspicious numeric survey response patterns")
    parser.add_argument("input_path")
    parser.add_argument("--rules", required=True)
    parser.add_argument("--output")
    parser.add_argument("--report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rules = load_rules(args.rules)
        frame = load_input(args.input_path, rules)
        run = score_run(frame, rules)
        output_path = write_scored(run.scored, args.input_path, args.output)
        print_summary(run.scored, output_path, run.skipped_scales)
        if args.report:
            write_report(run.scored, args.report, rules.id_column, run)
    except SurveyGuardError as exc:
        print(f"Error: {exc}")
        return 1
    return 0