import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pyreadstat


FIXTURE_CSV = Path("tests/fixtures/ess_mock.csv")
FIXTURE_RULES = Path("config/scale_logic.json")


def test_cli_creates_derived_scored_csv_and_summary(tmp_path):
    source = FIXTURE_CSV
    rules = FIXTURE_RULES
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
    assert len(output) == 33
    assert "quality_score" in output.columns
    assert "Processed: 33" in result.stdout
    assert "Not scored: 0" in result.stdout
    assert "Suspicious: 3" in result.stdout
    assert "Missing: 2" in result.stdout
    assert "Invalid: 2" in result.stdout
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
    source = FIXTURE_CSV
    rules = FIXTURE_RULES
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
    assert "- Processed respondents: 33" in report
    assert "- Suspicious respondents: 3" in report
    assert "| Straightlining | 4 | 12.12% |" in report
    assert "| Contradiction | 4 | 12.12% |" in report
    assert "| Mahalanobis | 4 | 12.12% |" in report
    assert "| 1032 | 33.33 | Straightlining_Satisfaction;Contradiction: trstplt>8 vs trstprl<2 |" in report
    assert "Straightlining_Trust_Institutions" in report


def test_cli_processes_xlsx_and_sav_inputs(tmp_path):
    rules = FIXTURE_RULES
    source = pd.read_csv(FIXTURE_CSV)
    source["stflife"] = pd.to_numeric(source["stflife"], errors="coerce").fillna(6)
    inputs = [
        tmp_path / "ess.xlsx",
        tmp_path / "ess.sav",
    ]
    source.to_excel(inputs[0], index=False)
    pyreadstat.write_sav(
        source,
        inputs[1],
        variable_value_labels={"trstprl": {0: "No trust at all", 10: "Complete trust"}},
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
        assert len(pd.read_csv(output_path)) == 33


def test_cli_reports_unsupported_extension_without_output(tmp_path):
    rules = FIXTURE_RULES
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
    source = FIXTURE_CSV
    rules = FIXTURE_RULES
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
    rules = FIXTURE_RULES
    input_path = tmp_path / "bad.csv"
    input_path.write_text("idno,trstprl\n1,1\n", encoding="utf-8")
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

def test_cli_rejects_legacy_rules_file_without_output(tmp_path):
    rules = tmp_path / "legacy.json"
    rules.write_text(json.dumps({
        "blocks": {"attitude_scale": {"columns": ["trstprl", "trstplt"], "min": 0, "max": 10}},
        "inverted_pairs": [["trstprl", "trstplt", "attitude_scale"]],
        "thresholds": {"mahalanobis_outlier": 6},
    }), encoding="utf-8")
    output_path = tmp_path / "scored.csv"

    result = subprocess.run(
        [sys.executable, "detect_anomalies.py", str(FIXTURE_CSV), "--rules", str(rules), "--output", str(output_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert result.stdout.startswith("Error: Legacy rules key 'blocks' is no longer supported")
    assert not output_path.exists()
