# file: rdagent/scenarios/data_science/scen/utils.py:122-174
# asked: {"lines": [124, 126, 127, 128, 130, 131, 132, 133, 134, 135, 136, 137, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 157, 158, 159, 160, 163, 164, 166, 167, 168, 169, 170, 172, 174], "branches": [[130, 131], [130, 139], [135, 136], [135, 137], [140, 141], [140, 157], [146, 147], [146, 149], [149, 150], [149, 151], [151, 152], [151, 153], [153, 140], [153, 154], [157, 158], [157, 163], [159, 160], [159, 163], [163, 164], [163, 174], [167, 168], [167, 172]]}
# gained: {"lines": [124, 126, 127, 128, 130, 131, 132, 133, 134, 135, 136, 137, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 157, 158, 159, 160, 163, 164, 166, 167, 168, 169, 170, 172, 174], "branches": [[130, 131], [130, 139], [135, 136], [135, 137], [140, 141], [140, 157], [146, 147], [146, 149], [149, 150], [149, 151], [151, 152], [151, 153], [153, 154], [157, 158], [157, 163], [159, 160], [163, 164], [167, 168], [167, 172]]}

import pandas as pd
import pytest
from rdagent.scenarios.data_science.scen.utils import preview_df


def test_preview_simple_small_dataframe():
    # Small dataframe with 3 columns to exercise the simple=True branch and small preview (<=15 cols)
    df = pd.DataFrame({
        "col1": [1, 2, 3],
        "col2": ["a", "b", "c"],
        "col3": [True, False, True],
    })

    out = preview_df(df, "small_file.csv", simple=True, show_nan_columns=False)

    # Basic expected parts
    assert "### small_file.csv:" in out
    assert "#### 1.DataFrame preview:" in out
    assert "It has 3 rows and 3 columns." in out

    # Simple listing of columns should appear and not include the "... and X more columns" suffix
    assert "The columns are:" in out
    assert "... and" not in out

    # Because dataframe has <=15 columns, the preview should contain the direct string of df.head(5)
    assert "#### 2.DataFrame preview:(only show the first 5 rows and 15 columns)" in out
    # The DataFrame preview should include the column names
    assert "col1" in out and "col2" in out and "col3" in out
    # No NaN summary should be present
    assert "Columns containing NaN values" not in out


def test_preview_simple_many_columns_truncation():
    # Create a dataframe with >100 columns to trigger the "... and X more columns" branch in simple mode
    num_cols = 105
    data = {f"c{i}": [i % 5] * 3 for i in range(num_cols)}
    df = pd.DataFrame(data)

    out = preview_df(df, "many_cols.csv", simple=True, show_nan_columns=False)

    assert "### many_cols.csv:" in out
    assert "#### 1.DataFrame preview:" in out
    # Should say it has 3 rows and 105 columns
    assert "It has 3 rows and 105 columns." in out

    # Because len(cols) > 100, we expect the "... and 5 more columns" suffix
    assert "The columns are:" in out
    assert "... and 5 more columns" in out

    # Because there are >15 columns, the DataFrame preview should show truncated columns and the extra message
    assert "#### 2.DataFrame preview:(only show the first 5 rows and 15 columns)" in out
    assert "... (showing first 15 of 105 columns)" in out


def test_preview_detailed_various_types_and_nan_columns():
    # Build a dataframe to exercise the detailed (simple=False) branch including:
    # - a boolean column to exercise the bool branch
    # - a column with few unique values (<10)
    # - a numeric column with many unique values and NaNs
    # - an object column with many unique values >=10 and some NaNs
    # Also make total columns >15 to exercise the preview truncation for the second section.
    n_rows = 12
    cols = {}

    # Boolean column (no NaNs so dtype remains bool)
    cols["bool_col"] = pd.Series(
        [True, False, True, True, False, True, True, False, True, False, True, True], dtype=bool
    )

    # Few unique values column
    vals_few = ["a", "b", "a", "c", "b", "a", "b", "c", "a", "b", "a", "c"]
    cols["few_uniques"] = pd.Series(vals_few, dtype=object)

    # Numeric column with many unique values and some NaNs
    num_vals = list(range(n_rows))
    num_vals[3] = float("nan")
    num_vals[7] = float("nan")
    cols["num_col"] = pd.Series(num_vals, dtype=float)

    # Object column with many unique values (>=10) and a NaN
    obj_vals = [f"val_{i}" for i in range(n_rows)]
    obj_vals[5] = None
    cols["obj_many"] = pd.Series(obj_vals, dtype=object)

    # Add filler columns to exceed 15 total columns
    for i in range(12):
        cols[f"filler_{i}"] = pd.Series([i] * n_rows)

    df = pd.DataFrame(cols)

    # Sanity: ensure we have >15 columns
    assert df.shape[1] > 15

    out = preview_df(df, "detailed.csv", simple=False, show_nan_columns=True)

    # Should include the detailed header and the "Here is some information about the columns:"
    assert "### detailed.csv:" in out
    assert "Here is some information about the columns:" in out

    # Bool column summary should indicate percent True and percent False
    assert "bool_col" in out
    assert "66.67% True" in out
    assert "33.33% False" in out

    # few_uniques branch should show number of unique values and list them
    assert "few_uniques" in out
    assert "has 3 unique values" in out
    # unique values list order may vary, check that the three expected values appear somewhere
    assert "a" in out and "b" in out and "c" in out

    # num_col should trigger numeric range output and mention nan values count (we set 2 NaNs)
    assert "num_col" in out
    assert "has range:" in out
    assert "2 nan values" in out

    # obj_many should trigger object handling with example values
    assert "obj_many" in out
    assert "Some example values" in out

    # show_nan_columns True: should list columns that contain NaNs (num_col and obj_many)
    assert "Columns containing NaN values:" in out
    assert "num_col" in out and "obj_many" in out

    # The second part preview should be present and truncated to first 15 columns list + message about total columns
    assert "#### 2.DataFrame preview:(only show the first 5 rows and 15 columns)" in out
    assert f"... (showing first 15 of {df.shape[1]} columns)" in out
