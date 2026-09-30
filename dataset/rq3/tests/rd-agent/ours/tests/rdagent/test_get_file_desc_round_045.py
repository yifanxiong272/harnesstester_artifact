import pytest
from pathlib import Path
import pandas as pd
import numpy as np

import rdagent.scenarios.qlib.experiment.utils as utils


def test_h5_multiindex_all_columns_round_045(monkeypatch, tmp_path):
    # Build a MultiIndex dataframe with REPORT_PERIOD and other columns
    dates = [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-02")]
    instruments = ["inst1", "inst2"]
    mi = pd.MultiIndex.from_product([dates, instruments], names=["date", "instrument"])

    # columns include a prefixed name starting with '$', a normal column, and REPORT_PERIOD
    data = {
        "$pref_col_1": np.arange(len(mi)),
        "normal_col": np.arange(len(mi)) + 100,
        "REPORT_PERIOD": np.array([1, 2, 3, 4]),
    }
    df = pd.DataFrame(data, index=mi)

    # Ensure deterministic behavior by making shuffle a no-op in the module under test
    monkeypatch.setattr(utils.random, "shuffle", lambda x: None)

    # Patch read_hdf used inside the function to return our prepared dataframe
    monkeypatch.setattr(utils.pd, "read_hdf", lambda p: df)

    desc = utils.get_file_desc(tmp_path / "sample.h5")

    # Assert high-level template rendered and DataFrame-derived pieces present
    assert "HDF5 Data File" in desc
    assert "Data Structure" in desc
    # Index branch should indicate MultiIndex and the instrument name
    assert "MultiIndex" in desc or "instrument" in desc
    # Should include a section showing data for the sampled instrument
    assert "Showing data for instrument" in desc
    # Should include the REPORT_PERIOD column name in the sample data text
    assert "REPORT_PERIOD" in desc


def test_h5_variable_list_round_045(monkeypatch, tmp_path):
    # Build a single-index dataframe (not MultiIndex) and test variable_list branch
    idx = [0, 1, 2]
    df = pd.DataFrame({"colA": [1, 2, 3], "colB": [4, 5, 6]}, index=idx)
    df.index.name = "idx_name"

    # Patch read_hdf to return this dataframe
    monkeypatch.setattr(utils.pd, "read_hdf", lambda p: df)
    # Also ensure shuffle is no-op to avoid nondeterminism in the unrelated branch
    monkeypatch.setattr(utils.random, "shuffle", lambda x: None)

    desc = utils.get_file_desc(tmp_path / "vars.h5", variable_list=["colA"])

    # Should indicate HDF5 and that Relevant Columns are shown
    assert "HDF5 Data File" in desc
    assert "Relevant Columns" in desc
    # Should include the chosen variable and its dtype representation
    assert "colA" in desc
    # dtype should be mentioned (int or similar); ensure colon-pair appears
    assert ":" in desc


def test_md_round_045(tmp_path):
    # Create a markdown file and verify markdown branch
    p = tmp_path / "readme.md"
    content = "# Title\n\nSome description here."
    p.write_text(content)

    desc = utils.get_file_desc(p)

    # Template should render with Markdown Documentation type and contain file content
    assert "Markdown Documentation" in desc
    assert "Some description here." in desc
    assert "# Title" in desc


def test_unsupported_round_045():
    # Unsupported extension should raise NotImplementedError with the expected message
    with pytest.raises(NotImplementedError) as exc:
        utils.get_file_desc(Path("unknown_file.txt"))
    assert "is not supported" in str(exc.value)
