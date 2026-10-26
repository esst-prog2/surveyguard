"""Streamlit web interface for SurveyGuard.

Run with: python -m streamlit run app.py
"""

from __future__ import annotations

import os
import re
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
    mahalanobis_count_note,
    render_report,
    report_overview,
    scale_results,
)
from surveyguard.scoring import score_run


CONFIG_DIR = Path(__file__).resolve().with_name("config")
UPLOAD_RULES = "Upload a rules file"
BUNDLED_RULES = "Bundled rules file"


def _natural_key(path: Path) -> list[int | str]:
    """Compare digit runs as numbers so ess2.json sorts before ess10.json."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def bundled_rules_files() -> list[Path]:
    """Top-level rules files shipped in config/; included module files live in subfolders."""
    return sorted(CONFIG_DIR.glob("*.json"), key=_natural_key)


@dataclass(frozen=True)
class RunResult:
    overview: ReportOverview
    detectors: pd.DataFrame
    flagged: pd.DataFrame
    report_markdown: str
    report_file_name: str
    cleaned_csv: bytes
    cleaned_file_name: str
    removed_count: int
    kept_count: int
    scales: pd.DataFrame
    mahalanobis_note: str
    skipped_scales: tuple[str, ...]
    skipped_rules: tuple[str, ...]

    @property
    def report_bytes(self) -> bytes:
        # Same bytes as the CLI's `--report` file, which write_text saves with the platform line ending.
        return self.report_markdown.replace("\n", os.linesep).encode("utf-8")


def run_surveyguard(
    data_name: str,
    data_bytes: bytes,
    rules_bytes: bytes | None = None,
    *,
    rules_path: str | Path | None = None,
) -> RunResult:
    """Score uploaded data with uploaded rules bytes or a bundled rules file, using the CLI pipeline."""
    if (rules_bytes is None) == (rules_path is None):
        raise ValueError("Pass exactly one of rules_bytes or rules_path")
    extension = Path(data_name).suffix.lower()
    with tempfile.TemporaryDirectory(prefix="surveyguard-") as workdir:
        if rules_path is None:
            # Relative include paths cannot be resolved from the temporary folder.
            uploaded_rules = Path(workdir) / "rules.json"
            uploaded_rules.write_bytes(rules_bytes)
            rules = load_rules(uploaded_rules, allow_include=False)
        else:
            rules = load_rules(rules_path)
        if extension not in SUPPORTED_INPUT_EXTENSIONS:
            # load_input rejects the extension before touching the file system.
            load_input(data_name, rules)
        input_path = Path(workdir) / f"input{extension}"
        input_path.write_bytes(data_bytes)
        frame = load_input(input_path, rules)
    run = score_run(frame, rules)
    scored = run.scored
    # Unscored respondents (<NA>) are not suspicious, so they stay in the cleaned data.
    keep = ~scored["suspicious"].fillna(False).to_numpy(dtype=bool)
    cleaned = frame.iloc[keep]
    return RunResult(
        overview=report_overview(scored),
        detectors=detector_results(scored),
        flagged=flagged_respondents(scored, rules.id_column),
        report_markdown=render_report(scored, rules.id_column, run),
        report_file_name=f"{Path(data_name).stem}_diagnostics.md",
        cleaned_csv=cleaned.to_csv(index=False).encode("utf-8"),
        cleaned_file_name=f"{Path(data_name).stem}_cleaned.csv",
        removed_count=int((~keep).sum()),
        kept_count=len(cleaned),
        scales=scale_results(run),
        mahalanobis_note=mahalanobis_count_note(run),
        skipped_scales=run.skipped_scales,
        skipped_rules=tuple(rule.label for rule in run.skipped_rules),
    )


def show_result(result: RunResult) -> None:
    st.subheader("Overview")
    processed, suspicious, average = st.columns(3)
    processed.metric("Processed respondents", result.overview.processed)
    suspicious.metric("Suspicious respondents", result.overview.suspicious)
    average.metric("Average quality score", _format_metric(result.overview.average_score))

    st.subheader("Detector results")
    table_column, chart_column = st.columns(2)
    table_column.dataframe(
        result.detectors,
        hide_index=True,
        column_config={"Percentage": st.column_config.NumberColumn(format="%.2f%%")},
    )
    chart_column.bar_chart(
        result.detectors,
        x="Detector",
        y="Percentage",
        x_label="Detector",
        y_label="Respondents triggered (%)",
        sort=False,
    )
    st.caption(result.mahalanobis_note)

    st.subheader("Detector-flagged respondents")
    if result.flagged.empty:
        st.info("No respondents were flagged.")
    else:
        suspicious_only = st.toggle("Show suspicious respondents only", key="suspicious_only")
        flagged = result.flagged[result.flagged["Suspicious"]] if suspicious_only else result.flagged
        if flagged.empty:
            st.info("No respondents are suspicious.")
        else:
            st.dataframe(
                flagged.astype({"Respondent": str}),
                hide_index=True,
                column_config={"Quality score": st.column_config.NumberColumn(format="%.2f")},
            )

    st.subheader("Scale results")
    # "-" marks a detector that does not run on the scale, so the count columns are shown as text.
    st.dataframe(
        result.scales.astype({"Straightlining": str, "Mahalanobis flags (scale-level)": str}),
        hide_index=True,
    )
    if result.skipped_scales or result.skipped_rules:
        st.info(
            f"Skipped scales: {', '.join(result.skipped_scales) or 'None'}. "
            f"Skipped contradiction rules: {'; '.join(result.skipped_rules) or 'None'}."
        )

    report_column, cleaned_column = st.columns(2)
    report_column.download_button(
        "Download diagnostic report",
        data=result.report_bytes,
        file_name=result.report_file_name,
        mime="text/markdown",
    )
    cleaned_column.download_button(
        "Download cleaned data (CSV)",
        data=result.cleaned_csv,
        file_name=result.cleaned_file_name,
        mime="text/csv",
    )
    st.caption(
        f"Cleaned data: removed {result.removed_count} suspicious respondents, kept {result.kept_count}."
    )


def main() -> None:
    st.set_page_config(page_title="SurveyGuard", layout="wide")
    st.title("SurveyGuard")
    st.caption("Detect suspicious numeric survey response patterns.")

    with st.sidebar:
        st.header("Inputs")
        data_file = st.file_uploader("Response data", type=["csv", "xlsx", "sav"])
        rules_source = st.radio("Rules source", [UPLOAD_RULES, BUNDLED_RULES], key="rules_source")
        rules_file = None
        bundled_path = None
        if rules_source == UPLOAD_RULES:
            rules_file = st.file_uploader("Rules configuration", type=["json"])
        else:
            bundled_path = st.selectbox(
                "Bundled rules file",
                bundled_rules_files(),
                format_func=lambda path: f"config/{path.name}",
                key="bundled_rules",
            )
        missing = [
            label
            for label, provided in (
                ("response data file", data_file is not None),
                ("rules file", rules_file is not None or bundled_path is not None),
            )
            if not provided
        ]
        if missing:
            st.info(f"Upload the {' and the '.join(missing)} to run SurveyGuard.")
        run_clicked = st.button("Run SurveyGuard", type="primary", disabled=bool(missing))
    rules_key = ("upload", rules_file.file_id) if rules_file is not None else ("bundled", str(bundled_path))
    run_key = None if missing else (data_file.file_id, rules_key)

    # Streamlit reruns the script on every interaction, so keep the last result
    # while its uploads are unchanged and drop it as soon as either one changes.
    stored = st.session_state.get("surveyguard_run")
    if stored is not None and stored[0] != run_key:
        del st.session_state["surveyguard_run"]

    if run_clicked:
        try:
            with st.spinner("Processing data..."):
                if rules_file is not None:
                    result = run_surveyguard(data_file.name, data_file.getvalue(), rules_file.getvalue())
                else:
                    result = run_surveyguard(data_file.name, data_file.getvalue(), rules_path=bundled_path)
        except SurveyGuardError as exc:
            st.session_state.pop("surveyguard_run", None)
            st.error(f"Error: {exc}")
        else:
            st.session_state["surveyguard_run"] = (run_key, result)
            # Only shown in the rerun that ran the analysis, not after later interactions.
            st.success("Analysis complete!")

    stored = st.session_state.get("surveyguard_run")
    if stored is not None:
        show_result(stored[1])
    elif not run_clicked:
        st.info("Upload the response data and rules files in the sidebar, then click Run SurveyGuard.")


if __name__ == "__main__":
    main()
