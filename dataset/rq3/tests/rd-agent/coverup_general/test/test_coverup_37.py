# file: rdagent/log/ui/utils.py:712-780
# asked: {"lines": [712, 713, 714, 716, 717, 718, 720, 721, 722, 723, 733, 734, 735, 736, 737, 738, 739, 742, 743, 744, 745, 746, 748, 749, 750, 751, 752, 753, 754, 755, 756, 759, 760, 761, 762, 764, 765, 766, 769, 770, 771, 772, 773, 774, 775, 776, 777, 779, 780], "branches": [[713, 714], [713, 716], [717, 718], [717, 720]]}
# gained: {"lines": [712, 713, 714, 716, 717, 718, 720, 721, 722, 723, 733, 734, 735, 736, 737, 738, 739, 742, 743, 744, 745, 746, 748, 749, 750, 751, 752, 753, 754, 755, 756, 759, 760, 761, 762, 764, 765, 766, 769, 770, 771, 772, 773, 774, 775, 776, 777, 779, 780], "branches": [[713, 714], [713, 716], [717, 718], [717, 720]]}

import pandas as pd
import pytest

from rdagent.log.ui.utils import get_statistics_df


def assert_percentage_series_close(series, expected_percentages, rel=1e-6):
    # helper to compare series values (floats) to expected mapping
    for idx, expected in expected_percentages.items():
        assert series.loc[idx] == pytest.approx(expected, rel=rel)


def test_get_statistics_df_with_int_any_medal():
    # Any Medal column is int dtype -> check_value = 0 branch
    df = pd.DataFrame(
        {
            "Made Submission": [1, 0, 1, 0],
            "Valid Submission": [1, 0, 0, 0],
            "Above Median": [0, 1, 0, 1],
            "Bronze": [0, 1, 0, 0],
            "Silver": [0, 0, 1, 0],
            "Gold": [1, 0, 0, 0],
            "Any Medal": [1, 0, 0, 0],  # int dtype
            "Best Result": ["gold", "bronze", "silver", "none"],
            "SOTA Exp": ["gold", "silver", "bronze", "above_median"],
            "SOTA Exp (to_submit)": ["gold", "bronze", "bronze", "valid_submission"],
        }
    )

    stat_df = get_statistics_df(df)

    # Should have three columns: overall, SOTA Exp, SOTA Exp (to_submit)
    assert stat_df.shape == (7, 3)
    # Check column names contain expected Chinese labels used in function
    assert "总体统计(%)" in stat_df.columns or "总体统计(%)" in stat_df.columns.tolist()
    # Validate numeric results:
    # total_stat counts of non-zero for the 7 tracked columns: Made Submission=2, Valid=1, Above Median=2, Bronze=1, Silver=1, Gold=1, Any Medal=1
    expected_total_percent = {
        "Made Submission": 2 / 4 * 100,
        "Valid Submission": 1 / 4 * 100,
        "Above Median": 2 / 4 * 100,
        "Bronze": 1 / 4 * 100,
        "Silver": 1 / 4 * 100,
        "Gold": 1 / 4 * 100,
        "Any Medal": 1 / 4 * 100,
    }
    assert_percentage_series_close(stat_df["总体统计(%)"], expected_total_percent)

    # SOTA Exp counts: gold=1,silver=1,bronze=1,above_median=1 -> made_submission=sum=4
    # Any Medal under se_counts = gold+silver+bronze =3
    # above_median = existing above_median (1) + Any Medal (3) =4
    # valid_submission = existing valid_submission (0) + above_median (4) =4
    expected_sota_percent = {
        "Made Submission": 4 / 4 * 100,
        "Valid Submission": 4 / 4 * 100,
        "Above Median": 4 / 4 * 100,
        "Bronze": 1 / 4 * 100,
        "Silver": 1 / 4 * 100,
        "Gold": 1 / 4 * 100,
        "Any Medal": 3 / 4 * 100,
    }
    assert_percentage_series_close(stat_df["SOTA Exp 统计(%)"], expected_sota_percent)

    # For to_submit: value_counts gold=1, bronze=2, valid_submission=1 -> made_submission=sum=4
    # Any Medal (to_submit) = gold+silver+bronze = 1+0+2 =3
    # above_median = existing above_median (0) + Any Medal (3) =3
    # valid_submission = existing valid_submission (1) + above_median (3) =4
    expected_sota_new_percent = {
        "Made Submission": 4 / 4 * 100,
        "Valid Submission": 4 / 4 * 100,
        "Above Median": 3 / 4 * 100,
        "Bronze": 2 / 4 * 100,
        "Silver": 0 / 4 * 100,
        "Gold": 1 / 4 * 100,
        "Any Medal": 3 / 4 * 100,
    }
    assert_percentage_series_close(stat_df["SOTA Exp (to_submit) 统计(%)"], expected_sota_new_percent)


def test_get_statistics_df_with_string_any_medal_contains_paren():
    # Any Medal column is string and first non-null contains '(' -> check_value = '0 (0.0%)'
    df = pd.DataFrame(
        {
            "Made Submission": ["0 (0.0%)", "1 (50.0%)", "0 (0.0%)"],
            "Valid Submission": ["1 (50.0%)", "1 (50.0%)", "0 (0.0%)"],
            "Above Median": ["0 (0.0%)", "0 (0.0%)", "0 (0.0%)"],
            "Bronze": ["bronze", "0 (0.0%)", "0 (0.0%)"],
            "Silver": ["0 (0.0%)", "0 (0.0%)", "0 (0.0%)"],
            "Gold": ["0 (0.0%)", "0 (0.0%)", "0 (0.0%)"],
            "Any Medal": ["0 (0.0%)", "0 (100.0%)", None],  # first non-null has '('
            "Best Result": ["bronze", "none", "none"],
            "SOTA Exp": ["bronze", "gold", "silver"],
            "SOTA Exp (to_submit)": ["bronze", None, "silver"],
        }
    )

    stat_df = get_statistics_df(df)

    # total rows = 3
    # Made Submission not-equal-to check_value count: only the second row -> 1
    assert stat_df.loc["Made Submission", "总体统计(%)"] == pytest.approx(1 / 3 * 100)
    # Valid Submission not-equal-to check_value count: rows 0 and 1 -> 2
    assert stat_df.loc["Valid Submission", "总体统计(%)"] == pytest.approx(2 / 3 * 100)
    # Above Median all equal -> 0
    assert stat_df.loc["Above Median", "总体统计(%)"] == pytest.approx(0.0)
    # Bronze overall count overwritten from Best Result: Best Result has one 'bronze'
    assert stat_df.loc["Bronze", "总体统计(%)"] == pytest.approx(1 / 3 * 100)

    # SOTA Exp counts: bronze=1,gold=1,silver=1 -> made_submission sum=3
    assert stat_df.loc["Made Submission", "SOTA Exp 统计(%)"] == pytest.approx(3 / 3 * 100)
    # Any Medal under SOTA Exp = gold+silver+bronze = 3 -> 100%
    assert stat_df.loc["Any Medal", "SOTA Exp 统计(%)"] == pytest.approx(3 / 3 * 100)


def test_get_statistics_df_with_string_any_medal_no_paren():
    # Any Medal column is string and first non-null does NOT contain '(' -> check_value = '0.0%'
    df = pd.DataFrame(
        {
            "Made Submission": ["0.0%", "50.0%", "0.0%", "100.0%"],
            "Valid Submission": ["0.0%", "50.0%", "0.0%", "0.0%"],
            "Above Median": ["0.0%", "0.0%", "100.0%", "0.0%"],
            "Bronze": ["0.0%", "bronze", "0.0%", "0.0%"],
            "Silver": ["0.0%", "0.0%", "silver", "0.0%"],
            "Gold": ["0.0%", "0.0%", "0.0%", "gold"],
            "Any Medal": ["0.0%", "50.0%", None, "100.0%"],  # first non-null '0.0%' -> no '('
            "Best Result": ["none", "bronze", "silver", "gold"],
            "SOTA Exp": ["bronze", "bronze", "silver", "gold"],
            "SOTA Exp (to_submit)": ["bronze", "bronze", "above_median", None],
        }
    )

    stat_df = get_statistics_df(df)

    # total rows = 4
    # Made Submission not equal to '0.0%': entries are at index 1 and 3 -> 2
    assert stat_df.loc["Made Submission", "总体统计(%)"] == pytest.approx(2 / 4 * 100)
    # Bronze from Best Result: one bronze -> 1/4*100
    assert stat_df.loc["Bronze", "总体统计(%)"] == pytest.approx(1 / 4 * 100)

    # SOTA Exp counts: bronze=2,silver=1,gold=1 -> Any Medal = 4
    assert stat_df.loc["Any Medal", "SOTA Exp 统计(%)"] == pytest.approx(4 / 4 * 100)
    # to_submit counts: bronze=2,above_median=1 -> made_submission sum=3
    assert stat_df.loc["Made Submission", "SOTA Exp (to_submit) 统计(%)"] == pytest.approx(3 / 4 * 100)
