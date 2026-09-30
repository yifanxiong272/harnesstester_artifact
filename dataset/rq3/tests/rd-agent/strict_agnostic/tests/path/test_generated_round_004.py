import types
import math
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import pytest

import rdagent.log.ui.utils as utils
from rdagent.log.ui.utils import UI_SETTING


def _make_times_info():
    # two loops with different step types to exercise exp_gen/coding/running accumulation
    t0 = datetime(2020, 1, 1, 0, 0, 0)
    times = {
        "loop1": {
            "exp_gen": {"start_time": t0, "end_time": t0 + timedelta(seconds=2)},
            "coding": {"start_time": t0 + timedelta(seconds=2), "end_time": t0 + timedelta(seconds=5)},
        },
        "loop2": {
            "running": {"start_time": t0 + timedelta(seconds=5), "end_time": t0 + timedelta(seconds=7)}
        },
    }
    return times


class _DummySotaSubmitWithAttr:
    def __init__(self, df):
        # normal object with 'result' attribute
        self.result = df


class _DummySotaSubmitAttrError:
    def __init__(self, df):
        # object that raises AttributeError when accessing .result, but stores the result inside __dict__
        # so the except branch which reads __dict__["result"] will be executed
        self.__dict__["result"] = df

    def __getattribute__(self, name):
        if name == "result":
            raise AttributeError("simulate old incompatible attribute access")
        return super().__getattribute__(name)


@pytest.fixture(autouse=True)
def restore_utils(monkeypatch):
    # ensure no test mutates module-level settings permanently
    orig_get_script_time = utils.get_script_time
    orig_load_times_info = utils.load_times_info
    orig_get_sota_exp_stat = utils.get_sota_exp_stat
    orig_get_score_stat = utils.get_score_stat
    orig_baseline = UI_SETTING.baseline_result_path

    yield

    # restore if available
    monkeypatch.setattr(utils, "get_script_time", orig_get_script_time, raising=False)
    monkeypatch.setattr(utils, "load_times_info", orig_load_times_info, raising=False)
    monkeypatch.setattr(utils, "get_sota_exp_stat", orig_get_sota_exp_stat, raising=False)
    monkeypatch.setattr(utils, "get_score_stat", orig_get_score_stat, raising=False)
    UI_SETTING.baseline_result_path = orig_baseline


def test_get_summary_df_normal_round_004(tmp_path, monkeypatch):
    # Setup: create a summary.pkl that will be read by get_summary_df
    k = "expA"
    summary = {
        k: {
            "competition": "compA",
            "loop_num": 1,
            "success_loop_num": 1,
            "made_submission_num": 1,
            "valid_submission_num": 0,
            "above_median_num": 0,
            "bronze_num": 0,
            "silver_num": 0,
            "gold_num": 0,
            "get_medal_num": 0,
            # placeholders that will be filled by get_sota_exp_stat/get_score_stat
        }
    }
    # write a pickle file (local filesystem only, deterministic)
    p = tmp_path / "summary.pkl"
    pd.to_pickle(summary, p)

    # create a stdout file to trigger get_script_time call
    stdout_file = tmp_path / f"{k}.stdout"
    stdout_file.write_text("log lines")

    # monkeypatch filesystem check of the summary name detection to use our tmp_path
    monkeypatch.chdir(tmp_path)

    # monkeypatch get_script_time to return a string-like script time
    monkeypatch.setattr(utils, "get_script_time", lambda _p: "0:00:01")

    # monkeypatch load_times_info to return structured times to exercise duration sums
    monkeypatch.setattr(utils, "load_times_info", lambda _p: _make_times_info())

    # Prepare get_sota_exp_stat side effects: first call returns a sota_submit with .result attr
    # second call returns best_valid with a report dict
    df_submit = pd.DataFrame({"ensemble": [0.8]}).set_index(pd.Index(["ensemble"]))

    def fake_get_sota_exp_stat(path, selector="auto"):
        if selector == "auto":
            return (_DummySotaSubmitWithAttr(df_submit), "lid_new", {"score": 0.6}, "sota_stat_new")
        else:
            return (None, "lid_best", {"score": 0.65}, "sota_stat_best")

    monkeypatch.setattr(utils, "get_sota_exp_stat", fake_get_sota_exp_stat)

    # get_score_stat returns (valid_improve, test_improve, submit_is_merge, merge_sota_rate)
    monkeypatch.setattr(utils, "get_score_stat", lambda *_args, **_kw: (True, False, False, 0.1))

    # baseline file present and matching compA
    baseline_csv = tmp_path / "baseline.csv"
    pd.DataFrame({"competition_id": ["compA"], "score": [0.7]}).to_csv(baseline_csv, index=False)
    UI_SETTING.baseline_result_path = str(baseline_csv)

    # Execute
    summary_out, df = utils.get_summary_df(tmp_path)

    # Assertions: summary_out keeps our key and df contains expected mapped values
    assert k in summary_out
    assert isinstance(df, pd.DataFrame)
    # Competition column is set
    assert df.loc[k, "Competition"] == "compA"
    # Script Time was propagated
    assert df.loc[k, "Script Time"] == "0:00:01"
    # Exec Time (derived from times) should be non-empty string
    assert isinstance(df.loc[k, "Exec Time"], str) and df.loc[k, "Exec Time"] != ""
    # Since made_submission_num > 0, Best Result should be at least 'made_submission'
    assert df.loc[k, "Best Result"] == "made_submission"
    # SOTA Exp Score (to_submit) should come from the returned submit report (0.6)
    assert df.loc[k, "SOTA Exp Score (to_submit)"] == 0.6
    # SOTA Exp Score (valid, to_submit) was 0.8 from .result ensemble -> numeric
    assert pytest.approx(float(df.loc[k, "SOTA Exp Score (valid, to_submit)"])) == 0.8


def test_get_summary_df_attribute_error_and_compare_exception_round_004(tmp_path, monkeypatch):
    # This test triggers the AttributeError branch when reading .result and also compare_score exception
    k = "expB"
    # Put values that will cause the division by zero inside compare_score (baseline_score == 0)
    summary = {
        k: {
            "competition": "compB",
            "loop_num": 2,
            "success_loop_num": 2,
            "made_submission_num": 0,
            "valid_submission_num": 0,
            "above_median_num": 0,
            "bronze_num": 0,
            "silver_num": 0,
            "gold_num": 0,
            "get_medal_num": 0,
        }
    }
    p = tmp_path / "summary.pkl"
    pd.to_pickle(summary, p)

    # create stdout file so script_time path exists branch is taken
    stdout_file = tmp_path / f"{k}.stdout"
    stdout_file.write_text("log lines")

    monkeypatch.chdir(tmp_path)

    # get_script_time returns None to ensure None values handled through pipeline
    monkeypatch.setattr(utils, "get_script_time", lambda _p: None)

    # times info with a single running step so running_time path exercised
    def make_times_single():
        t0 = datetime(2021, 1, 1, 0, 0, 0)
        return {"loop1": {"running": {"start_time": t0, "end_time": t0 + timedelta(seconds=3)}}}

    monkeypatch.setattr(utils, "load_times_info", lambda _p: make_times_single())

    # For first get_sota_exp_stat (selector='auto') return an object that raises AttributeError when accessing .result
    # but has __dict__["result"] available as a DataFrame whose ensemble value is a string (to trigger string replacement)
    df_submit_str = pd.DataFrame({"ensemble": ["not_a_number"]}).set_index(pd.Index(["ensemble"]))

    def fake_get_sota_exp_stat(path, selector="auto"):
        if selector == "auto":
            # return object that will force the except branch
            return (_DummySotaSubmitAttrError(df_submit_str), "lid_new_b", {"score": 0.1}, "sota_stat_new_b")
        else:
            # return best_valid with a numeric score to set v["sota_exp_score"]
            return (None, "lid_best_b", {"score": 0.9}, "sota_stat_best_b")

    monkeypatch.setattr(utils, "get_sota_exp_stat", fake_get_sota_exp_stat)

    # score stat: return booleans
    monkeypatch.setattr(utils, "get_score_stat", lambda *_args, **_kw: (False, True, True, 0.2))

    # baseline file with score 0 to cause ZeroDivisionError inside compare_score
    baseline_csv = tmp_path / "baseline.csv"
    pd.DataFrame({"competition_id": ["compB"], "score": [0.0]}).to_csv(baseline_csv, index=False)
    UI_SETTING.baseline_result_path = str(baseline_csv)

    # Run
    summary_out, df = utils.get_summary_df(tmp_path)

    # Assertions
    assert k in summary_out
    # Since no made/valid/above_median/bronze/silver/gold, Best Result remains NaN or empty
    # But we ensure the row exists and has expected competition string
    assert df.loc[k, "Competition"] == "compB"
    # Script Time was None in summary, so DataFrame receives None
    assert pd.isna(df.loc[k, "Script Time"]) or df.loc[k, "Script Time"] is None

    # The SOTA Exp Score (to_submit) should be numeric (from best_valid)
    assert df.loc[k, "SOTA Exp Score"] == 0.9

    # Because SOTA Exp Score (valid, to_submit) was a string initially ("not_a_number"), the replacement code sets it to 0.0
    assert df.loc[k, "SOTA Exp Score (valid, to_submit)"] == 0.0

    # Ours - Base should be computed (sota_exp_score - baseline_score) => 0.9 - 0.0 = 0.9
    assert pytest.approx(df.loc[k, "Ours - Base"]) == 0.9

    # Compare-based columns that call compare_score with baseline_score == 0 should produce None due to exception
    assert pd.isna(df.loc[k, "Ours vs Base"]) or df.loc[k, "Ours vs Base"] is None
    assert pd.isna(df.loc[k, "Ours vs Bronze"]) or df.loc[k, "Ours vs Bronze"] is None

    # Ensure type coercion did not raise and final result is a DataFrame
    assert isinstance(df, pd.DataFrame)
