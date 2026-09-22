import subprocess
import sys
from pathlib import Path

import pandas as pd


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