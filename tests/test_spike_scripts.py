import io
import urllib.error
import zipfile

import numpy as np
import pandas as pd
import pytest

import prepare_data
from run_spike import exact_five_percent_threshold


EXT_COLUMNS = [f"EXT{i}" for i in range(1, 11)]


def test_exact_five_percent_threshold_hand_computed():
    # n = 20 -> target = 1; threshold = (19 + 20) / 2
    assert exact_five_percent_threshold(pd.Series(range(1, 21))) == 19.5
    with_missing = pd.Series([*range(1, 21), np.nan])
    assert exact_five_percent_threshold(with_missing) == 19.5


def test_exact_five_percent_threshold_rejects_tie():
    # The two largest values are both 20, so no threshold isolates exactly one value.
    tied = pd.Series(list(range(1, 19)) + [20, 20])
    with pytest.raises(ValueError, match="exact 5% threshold impossible"):
        exact_five_percent_threshold(tied)


def test_exact_five_percent_threshold_rejects_small_sample():
    # n = 19 -> target = int(0.95) = 0
    with pytest.raises(ValueError, match="enough rows for a 5% target"):
        exact_five_percent_threshold(pd.Series(range(1, 20)))


def zip_bytes(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def ext_table(complete_rows: int, columns=EXT_COLUMNS, incomplete_rows: int = 0) -> str:
    frame = pd.DataFrame([[3] * len(columns)] * complete_rows, columns=columns, dtype=float)
    if incomplete_rows:
        incomplete = pd.DataFrame([[np.nan] * len(columns)] * incomplete_rows, columns=columns)
        frame = pd.concat([incomplete, frame], ignore_index=True)
    return frame.to_csv(sep="\t", index=False)


def serve(monkeypatch, payload: bytes) -> None:
    monkeypatch.setattr(prepare_data.urllib.request, "urlopen", lambda request: io.BytesIO(payload))


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_prepare_data_network_failure_exits_with_one(workdir, monkeypatch, capsys):
    def fail(request):
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(prepare_data.urllib.request, "urlopen", fail)
    assert prepare_data.main() == 1
    assert "Error:" in capsys.readouterr().err
    assert not (workdir / "spike_data.csv").exists()


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"not a zip archive", "zip"),
        (zip_bytes({"readme.txt": "no data"}), ".csv vagy .tsv"),
        (zip_bytes({"data.csv": ext_table(1000, columns=EXT_COLUMNS[:-1])}), "EXT10"),
        (zip_bytes({"data.csv": ext_table(999, incomplete_rows=5)}), "999"),
    ],
    ids=["corrupt-zip", "no-table", "missing-column", "too-few-rows"],
)
def test_prepare_data_expected_failures_exit_with_one(workdir, monkeypatch, capsys, payload, message):
    serve(monkeypatch, payload)
    assert prepare_data.main() == 1
    err = capsys.readouterr().err
    assert err.startswith("Error:")
    assert message.lower() in err.lower()
    assert not (workdir / "spike_data.csv").exists()


def test_prepare_data_does_not_swallow_unexpected_errors(workdir, monkeypatch):
    def explode(request):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(prepare_data.urllib.request, "urlopen", explode)
    with pytest.raises(RuntimeError, match="unexpected"):
        prepare_data.main()


def test_prepare_data_writes_exactly_1000_complete_rows(workdir, monkeypatch):
    serve(monkeypatch, zip_bytes({"data.csv": ext_table(1200, incomplete_rows=1)}))
    assert prepare_data.main() == 0
    written = pd.read_csv(workdir / "spike_data.csv")
    assert list(written.columns) == EXT_COLUMNS
    assert len(written) == 1000
    assert not written.isna().any().any()
