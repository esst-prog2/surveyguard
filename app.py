"""Streamlit web interface for SurveyGuard.

Run with: python -m streamlit run app.py
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

from surveyguard.config import load_rules
from surveyguard.errors import SurveyGuardError
from surveyguard.io import SUPPORTED_INPUT_EXTENSIONS, load_input
from surveyguard.reporting import (
    ReportOverview,
    _format_metric,
    detector_results,
    flagged_respondents,
    render_report,
    report_overview,
)
from surveyguard.scoring import score_dataframe


@dataclass(frozen=True)
class RunResult:
    overview: ReportOverview
    detectors: pd.DataFrame
    flagged: pd.DataFrame
    report_markdown: str
    report_file_name: str

    @property
    def report_bytes(self) -> bytes:
        # Same bytes as the CLI's `--report` file, which write_text saves with the platform line ending.
        return self.report_markdown.replace("\n", os.linesep).encode("utf-8")


def run_surveyguard(data_name: str, data_bytes: bytes, rules_bytes: bytes) -> RunResult:
    """Score uploaded files with the same pipeline as the CLI."""
    extension = Path(data_name).suffix.lower()
    with tempfile.TemporaryDirectory(prefix="surveyguard-") as workdir:
        rules_path = Path(workdir) / "rules.json"
        rules_path.write_bytes(rules_bytes)
        rules = load_rules(rules_path)
        if extension not in SUPPORTED_INPUT_EXTENSIONS:
            # load_input rejects the extension before touching the file system.
            load_input(data_name, rules)
        input_path = Path(workdir) / f"input{extension}"
        input_path.write_bytes(data_bytes)
        frame = load_input(input_path, rules)
    scored = score_dataframe(frame, rules)
    return RunResult(
        overview=report_overview(scored),
        detectors=detector_results(scored),
        flagged=flagged_respondents(scored, rules.id_column),
        report_markdown=render_report(scored, rules.id_column),
        report_file_name=f"{Path(data_name).stem}_diagnostics.md",
    )


def show_result(result: RunResult) -> None:
    st.subheader("Overview")
    processed, suspicious, average = st.columns(3)
    processed.metric("Processed respondents", result.overview.processed)
    suspicious.metric("Suspicious respondents", result.overview.suspicious)
    average.metric("Average quality score", _format_metric(result.overview.average_score))

    st.subheader("Detector results")
    st.dataframe(
        result.detectors,
        hide_index=True,
        column_config={"Percentage": st.column_config.NumberColumn(format="%.2f%%")},
    )

    st.subheader("Detector-flagged respondents")
    if result.flagged.empty:
        st.info("No respondents were flagged.")
    else:
        st.dataframe(
            result.flagged.astype({"Respondent": str}),
            hide_index=True,
            column_config={"Quality score": st.column_config.NumberColumn(format="%.2f")},
        )

    st.download_button(
        "Download diagnostic report",
        data=result.report_bytes,
        file_name=result.report_file_name,
        mime="text/markdown",
    )


def main() -> None:
    st.set_page_config(page_title="SurveyGuard", layout="wide")
    st.title("SurveyGuard")
    st.caption("Detect suspicious numeric survey response patterns.")

    data_file = st.file_uploader("Response data", type=["csv", "xlsx", "sav"])
    rules_file = st.file_uploader("Rules configuration", type=["json"])
    missing = [
        label
        for label, upload in (("response data file", data_file), ("rules file", rules_file))
        if upload is None
    ]
    if missing:
        st.info(f"Upload the {' and the '.join(missing)} to run SurveyGuard.")
    run_key = None if missing else (data_file.file_id, rules_file.file_id)

    # Streamlit reruns the script on every interaction, so keep the last result
    # while its uploads are unchanged and drop it as soon as either one changes.
    stored = st.session_state.get("surveyguard_run")
    if stored is not None and stored[0] != run_key:
        del st.session_state["surveyguard_run"]

    if st.button("Run SurveyGuard", type="primary", disabled=bool(missing)):
        try:
            result = run_surveyguard(data_file.name, data_file.getvalue(), rules_file.getvalue())
        except SurveyGuardError as exc:
            st.session_state.pop("surveyguard_run", None)
            st.error(f"Error: {exc}")
        else:
            st.session_state["surveyguard_run"] = (run_key, result)

    stored = st.session_state.get("surveyguard_run")
    if stored is not None:
        show_result(stored[1])


if __name__ == "__main__":
    main()
