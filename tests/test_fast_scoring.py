from pathlib import Path

import pandas as pd
import pyreadstat

from surveyguard.config import load_rules
from surveyguard.io import load_input
from surveyguard.scoring import score_dataframe


ESS_MOCK_CSV = Path("tests/fixtures/ess_mock.csv")
ESS_RULES = Path("config/scale_logic.json")


def _numeric_ess_mock() -> pd.DataFrame:
    # SPSS numeric columns cannot hold the fixture's "refused" text, so that one cell becomes a valid 6.
    source = pd.read_csv(ESS_MOCK_CSV)
    source["stflife"] = pd.to_numeric(source["stflife"], errors="coerce").fillna(6)
    return source


def _write_labelled_sav(source: pd.DataFrame, path: Path) -> Path:
    pyreadstat.write_sav(
        source,
        path,
        column_labels={column: f"Label of {column}" for column in source.columns},
        variable_value_labels={"trstprl": {0: "No trust at all", 10: "Complete trust", 77: "Refusal"}},
    )
    return path


def _result_columns(scored: pd.DataFrame, source: pd.DataFrame) -> pd.DataFrame:
    return scored[[column for column in scored.columns if column not in source.columns]]


# Input metadata


def test_sav_input_discards_spss_metadata_and_keeps_raw_codes(tmp_path):
    rules = load_rules(ESS_RULES)
    source = _numeric_ess_mock()
    path = _write_labelled_sav(source, tmp_path / "ess.sav")
    assert pd.read_spss(path, convert_categoricals=False).attrs["column_labels"]

    loaded = load_input(path, rules)

    assert loaded.attrs == {}
    assert loaded["trstprl"].tolist() == source["trstprl"].astype(float).tolist()


def test_csv_and_xlsx_inputs_carry_no_metadata(tmp_path):
    rules = load_rules(ESS_RULES)
    xlsx_path = tmp_path / "ess.xlsx"
    pd.read_csv(ESS_MOCK_CSV).to_excel(xlsx_path, index=False)

    assert load_input(ESS_MOCK_CSV, rules).attrs == {}
    assert load_input(xlsx_path, rules).attrs == {}


def test_sav_results_equal_csv_results(tmp_path):
    rules = load_rules(ESS_RULES)
    source = _numeric_ess_mock()
    csv_path = tmp_path / "ess.csv"
    source.to_csv(csv_path, index=False)
    sav_path = _write_labelled_sav(source, tmp_path / "ess.sav")

    from_csv = score_dataframe(load_input(csv_path, rules), rules)
    from_sav = score_dataframe(load_input(sav_path, rules), rules)

    # SPSS stores the item columns as doubles (4.0), so only the appended result columns are compared as text.
    assert _result_columns(from_sav, source).to_csv(index=False) == _result_columns(from_csv, source).to_csv(index=False)
    assert from_sav["idno"].tolist() == from_csv["idno"].tolist()
