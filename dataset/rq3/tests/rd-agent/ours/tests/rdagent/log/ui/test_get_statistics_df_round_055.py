import pandas as pd
import pytest

from rdagent.log.ui.utils import get_statistics_df

# Tests for get_statistics_df covering int Any Medal dtype, string Any Medal with and without parentheses.

def _compute_expected_se_counts(series: pd.Series) -> pd.Series:
    # Reproduce the same in-function mutation logic used by get_statistics_df
    se_counts = series.value_counts(dropna=True)
    se_counts.loc["made_submission"] = se_counts.sum()
    se_counts.loc["Any Medal"] = se_counts.get("gold", 0) + se_counts.get("silver", 0) + se_counts.get("bronze", 0)
    se_counts.loc["above_median"] = se_counts.get("above_median", 0) + se_counts.get("Any Medal", 0)
    se_counts.loc["valid_submission"] = se_counts.get("valid_submission", 0) + se_counts.get("above_median", 0)
    return se_counts


def test_any_medal_int_round_055():
    # Any Medal column is integer -> check_value == 0 branch
    rows = [
        {
            "Made Submission": 1,
            "Valid Submission": 1,
            "Above Median": 0,
            "Bronze": 0,
            "Silver": 0,
            "Gold": 0,
            "Any Medal": 0,
            "Best Result": "bronze",
            "SOTA Exp": "gold",
            "SOTA Exp (to_submit)": "gold",
        },
        {
            "Made Submission": 0,
            "Valid Submission": 1,
            "Above Median": 1,
            "Bronze": 1,
            "Silver": 0,
            "Gold": 0,
            "Any Medal": 1,
            "Best Result": "silver",
            "SOTA Exp": "silver",
            "SOTA Exp (to_submit)": None,
        },
        {
            "Made Submission": 0,
            "Valid Submission": 0,
            "Above Median": 1,
            "Bronze": 0,
            "Silver": 1,
            "Gold": 0,
            "Any Medal": 0,
            "Best Result": "gold",
            "SOTA Exp": "bronze",
            "SOTA Exp (to_submit)": "bronze",
        },
        {
            "Made Submission": 1,
            "Valid Submission": 0,
            "Above Median": 0,
            "Bronze": 0,
            "Silver": 0,
            "Gold": 1,
            "Any Medal": 2,
            "Best Result": "bronze",
            "SOTA Exp": "above_median",
            "SOTA Exp (to_submit)": "none",
        },
    ]

    df = pd.DataFrame(rows)
    # ensure Any Medal is integer dtype
    df["Any Medal"] = df["Any Medal"].astype(int)

    stat_df = get_statistics_df(df)

    # Column names come from the function (unicode Chinese strings)
    total_col = "\u603b\u4f53\u7edf\u8ba1(%)"
    sota_col = "SOTA Exp \u7edf\u8ba1(%)"
    sota_new_col = "SOTA Exp (to_submit) \u7edf\u8ba1(%)"

    assert total_col in stat_df.columns
    assert sota_col in stat_df.columns
    assert sota_new_col in stat_df.columns

    n = df.shape[0]

    # total_stat expected: (column != 0) counts then Bronze/Silver/Gold overwritten by Best Result counts
    expected_made = (df["Made Submission"] != 0).sum() / n * 100
    assert stat_df.loc["Made Submission", total_col] == pytest.approx(expected_made)

    # Bronze should be overwritten by Best Result counts
    bronze_count = df["Best Result"].value_counts().get("bronze", 0)
    expected_bronze = bronze_count / n * 100
    assert stat_df.loc["Bronze", total_col] == pytest.approx(expected_bronze)

    # Check SOTA Exp computed percentages via helper
    se_counts = _compute_expected_se_counts(df["SOTA Exp"])  # mutated counts
    expected_sota_made = se_counts.get("made_submission", 0) / n * 100
    assert stat_df.loc["Made Submission", sota_col] == pytest.approx(expected_sota_made)

    # Check SOTA Exp (to_submit)
    se_counts_new = df["SOTA Exp (to_submit)"].value_counts(dropna=True)
    # reproduce mutation for to_submit series to mirror function
    se_counts_new.loc["made_submission"] = se_counts_new.sum()
    se_counts_new.loc["Any Medal"] = se_counts_new.get("gold", 0) + se_counts_new.get("silver", 0) + se_counts_new.get("bronze", 0)
    se_counts_new.loc["above_median"] = se_counts_new.get("above_median", 0) + se_counts_new.get("Any Medal", 0)
    se_counts_new.loc["valid_submission"] = se_counts_new.get("valid_submission", 0) + se_counts_new.get("above_median", 0)

    expected_sota_new_made = se_counts_new.get("made_submission", 0) / n * 100
    assert stat_df.loc["Made Submission", sota_new_col] == pytest.approx(expected_sota_new_made)


def test_any_medal_str_with_parenthesis_round_055():
    # Any Medal is string and sample contains '(', so check_value == '0 (0.0%)' branch
    rows = [
        {
            "Made Submission": 1,
            "Valid Submission": 1,
            "Above Median": 0,
            "Bronze": 0,
            "Silver": 0,
            "Gold": 0,
            "Any Medal": "0 (0.0%)",
            "Best Result": "bronze",
            "SOTA Exp": "gold",
            "SOTA Exp (to_submit)": "gold",
        },
        {
            "Made Submission": 0,
            "Valid Submission": 0,
            "Above Median": 1,
            "Bronze": 1,
            "Silver": 0,
            "Gold": 0,
            "Any Medal": "1 (25.0%)",
            "Best Result": "silver",
            "SOTA Exp": "silver",
            "SOTA Exp (to_submit)": None,
        },
    ]

    df = pd.DataFrame(rows)
    stat_df = get_statistics_df(df)

    total_col = "\u603b\u4f53\u7edf\u8ba1(%)"
    assert stat_df.loc["Made Submission", total_col] == pytest.approx((df["Made Submission"] != "0 (0.0%)").sum() / df.shape[0] * 100)

    # Ensure that when sample contains '(', check_value used is the full '0 (0.0%)' string
    # So an exact string match should produce False for entries equal to that string
    # Confirm index name exists and Bronze value comes from Best Result counts
    bronze_count = df["Best Result"].value_counts().get("bronze", 0)
    assert stat_df.loc["Bronze", total_col] == pytest.approx(bronze_count / df.shape[0] * 100)


def test_any_medal_str_without_parenthesis_round_055():
    # Any Medal is string and sample does NOT contain '(', so check_value == '0.0%' branch
    rows = [
        {
            "Made Submission": 1,
            "Valid Submission": 0,
            "Above Median": 1,
            "Bronze": 0,
            "Silver": 0,
            "Gold": 0,
            "Any Medal": "0.0%",
            "Best Result": "bronze",
            "SOTA Exp": "bronze",
            "SOTA Exp (to_submit)": "bronze",
        },
        {
            "Made Submission": 0,
            "Valid Submission": 1,
            "Above Median": 0,
            "Bronze": 1,
            "Silver": 0,
            "Gold": 0,
            "Any Medal": "1.0%",
            "Best Result": "bronze",
            "SOTA Exp": "gold",
            "SOTA Exp (to_submit)": None,
        },
        {
            "Made Submission": 0,
            "Valid Submission": 0,
            "Above Median": 0,
            "Bronze": 0,
            "Silver": 1,
            "Gold": 0,
            "Any Medal": "0.0%",
            "Best Result": "silver",
            "SOTA Exp": "silver",
            "SOTA Exp (to_submit)": "none",
        },
    ]

    df = pd.DataFrame(rows)
    stat_df = get_statistics_df(df)

    total_col = "\u603b\u4f53\u7edf\u8ba1(%)"

    # check_value should be '0.0%'; ensure that comparison works as expected
    expected_made = (df["Made Submission"] != "0.0%").sum() / df.shape[0] * 100
    # Since Made Submission column holds integers, comparing to string yields True for all non-NaN entries
    # but function compares to check_value (string), so (int != '0.0%') will be True for every int -> count = number of rows
    assert stat_df.loc["Made Submission", total_col] == pytest.approx(expected_made)

    # Validate that SOTA Exp (to_submit) has been computed and is numeric
    sota_new_col = "SOTA Exp (to_submit) \u7edf\u8ba1(%)"
    assert sota_new_col in stat_df.columns
    # The value should be finite numeric percentage
    val = stat_df.loc["Made Submission", sota_new_col]
    assert isinstance(val, float)
    assert not pd.isna(val)
