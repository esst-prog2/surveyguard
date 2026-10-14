import subprocess
import sys
from pathlib import Path

import pandas as pd
import pyreadstat


def test_cli_creates_derived_scored_csv_and_summary(tmp_path):
    source = Path("tests/fixtures/survey.csv")
    rules = Path("tests/fixtures/rules.json")
    input_path = tmp_path / "wave1_raw.csv"
    input_path.write_bytes(source.read_bytes())
    result = subprocess.run(
        [sys.executable, "detect_anomalies.py", str(input_path), "--rules", str(rules)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    output_path = tmp_path / "wave1_scored.csv"
    assert output_path.exists()
    output = pd.read_csv(output_path)
    assert len(output) == 7
    assert "quality_score" in output.columns
    assert "Processed: 7" in result.stdout
    assert "Not scored: 0" in result.stdout
    assert "Suspicious:" in result.stdout
    assert f"Output: {output_path}" in result.stdout

    explicit_path = tmp_path / "explicit_scored.csv"
    explicit_result = subprocess.run(
        [sys.executable, "detect_anomalies.py", str(input_path), "--rules", str(rules), "--output", str(explicit_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert explicit_result.returncode == 0, explicit_result.stdout + explicit_result.stderr
    assert explicit_path.exists()


def test_cli_writes_markdown_report_with_metrics_and_reasons(tmp_path):
    source = Path("tests/fixtures/survey.csv")
    rules = Path("tests/fixtures/rules.json")
    input_path = tmp_path / "survey.csv"
    input_path.write_bytes(source.read_bytes())
    report_path = tmp_path / "diagnostics.md"

    result = subprocess.run(
        [
            sys.executable,
            "detect_anomalies.py",
            str(input_path),
            "--rules",
            str(rules),
            "--report",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    report = report_path.read_text(encoding="utf-8")
    assert "- Processed respondents: 7" in report
    assert "- Suspicious respondents:" in report
    assert "| Straightlining |" in report
    assert "| Contradiction |" in report
    assert "| Mahalanobis |" in report
    assert "Straightlining_Error:attitude_scale" in report


def test_cli_processes_xlsx_and_sav_inputs(tmp_path):
    rules = Path("tests/fixtures/rules.json")
    source = pd.read_csv("tests/fixtures/survey.csv")
    source["Q1"] = pd.to_numeric(source["Q1"], errors="coerce").fillna(3)
    inputs = [
        tmp_path / "survey.xlsx",
        tmp_path / "survey.sav",
    ]
    source.to_excel(inputs[0], index=False)
    pyreadstat.write_sav(
        source,
        inputs[1],
        variable_value_labels={"Q1": {1: "One", 2: "Two", 3: "Three", 4: "Four"}},
    )

    for input_path in inputs:
        output_path = tmp_path / f"{input_path.stem}_scored.csv"
        result = subprocess.run(
            [
                sys.executable,
                "detect_anomalies.py",
                str(input_path),
                "--rules",
                str(rules),
                "--output",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert len(pd.read_csv(output_path)) == 7


def test_cli_reports_unsupported_extension_without_output(tmp_path):
    rules = Path("tests/fixtures/rules.json")
    input_path = tmp_path / "survey.json"
    output_path = tmp_path / "scored.csv"
    input_path.write_text("{}", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "detect_anomalies.py",
            str(input_path),
            "--rules",
            str(rules),
            "--output",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Unsupported input extension" in result.stdout
    assert not output_path.exists()


def test_cli_fails_explicitly_when_report_path_is_directory(tmp_path):
    source = Path("tests/fixtures/survey.csv")
    rules = Path("tests/fixtures/rules.json")
    input_path = tmp_path / "survey.csv"
    report_path = tmp_path / "report-directory"
    input_path.write_bytes(source.read_bytes())
    report_path.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            "detect_anomalies.py",
            str(input_path),
            "--rules",
            str(rules),
            "--report",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert f"Could not write report {report_path}" in result.stdout


def test_cli_rejects_missing_question_column(tmp_path):
    rules = Path("tests/fixtures/rules.json")
    input_path = tmp_path / "bad.csv"
    input_path.write_text("respondent_id,Q1\nr1,1\n", encoding="utf-8")
    output_path = tmp_path / "explicit.csv"
    result = subprocess.run(
        [sys.executable, "detect_anomalies.py", str(input_path), "--rules", str(rules), "--output", str(output_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "Missing configured question columns" in result.stdout
    assert not output_path.exists()