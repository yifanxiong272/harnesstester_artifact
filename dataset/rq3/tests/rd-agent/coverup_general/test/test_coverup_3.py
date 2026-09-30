# file: rdagent/log/ui/utils.py:432-661
# asked: {"lines": [432, 452, 453, 454, 455, 457, 459, 460, 461, 462, 464, 466, 468, 469, 471, 472, 473, 474, 475, 477, 478, 479, 480, 481, 482, 484, 485, 486, 487, 488, 491, 492, 494, 495, 497, 498, 499, 500, 501, 502, 504, 505, 506, 507, 508, 509, 510, 512, 513, 515, 516, 517, 552, 556, 557, 558, 560, 561, 562, 563, 564, 565, 566, 567, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 581, 582, 583, 584, 585, 586, 587, 588, 589, 590, 591, 592, 593, 594, 595, 596, 597, 598, 599, 600, 602, 603, 604, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 617, 618, 619, 620, 621, 622, 623, 624, 625, 626, 627, 629, 631, 632, 633, 634, 635, 636, 637, 638, 639, 640, 641, 642, 643, 644, 645, 646, 647, 648, 649, 650, 651, 652, 653, 661], "branches": [[454, 455], [454, 457], [459, 460], [459, 515], [461, 462], [461, 464], [471, 472], [471, 484], [472, 471], [472, 473], [477, 478], [477, 479], [479, 480], [479, 481], [481, 472], [481, 482], [504, 505], [504, 512], [557, 558], [557, 560], [561, 562], [561, 563], [569, 570], [569, 629], [578, 579], [578, 581], [583, 584], [583, 585], [586, 587], [586, 588], [589, 590], [589, 591], [592, 593], [592, 594], [595, 596], [595, 597], [598, 599], [598, 600], [603, 604], [603, 606], [617, 618], [617, 619]]}
# gained: {"lines": [432, 452, 453, 454, 455, 457, 459, 460, 461, 462, 466, 468, 469, 471, 472, 473, 474, 475, 477, 478, 479, 480, 481, 482, 484, 485, 486, 487, 488, 491, 492, 494, 495, 497, 498, 499, 500, 501, 502, 504, 505, 506, 507, 508, 509, 510, 512, 513, 515, 516, 517, 552, 556, 557, 558, 560, 561, 563, 564, 565, 566, 567, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 581, 582, 583, 584, 585, 586, 587, 588, 589, 591, 592, 594, 595, 597, 598, 600, 602, 603, 604, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 617, 618, 619, 620, 621, 622, 623, 624, 625, 626, 627, 629, 631, 632, 633, 634, 635, 636, 637, 638, 639, 640, 641, 642, 643, 644, 645, 646, 647, 648, 649, 650, 651, 652, 653, 661], "branches": [[454, 455], [454, 457], [459, 460], [459, 515], [461, 462], [471, 472], [471, 484], [472, 471], [472, 473], [477, 478], [477, 479], [479, 480], [479, 481], [481, 482], [504, 505], [557, 558], [561, 563], [569, 570], [569, 629], [578, 581], [583, 584], [586, 587], [589, 591], [592, 594], [595, 597], [598, 600], [603, 604], [617, 618]]}

import pandas as pd
import math
import types
from pathlib import Path
import pytest
from datetime import datetime, timedelta
import numpy as np

import rdagent.log.ui.utils as utils
from rdagent.log.ui import conf as ui_conf


def make_sota_submit_obj(result_df):
    # Create object that raises AttributeError when accessing .result, but has __dict__['result']
    class SotaSubmit:
        def __getattribute__(self, name):
            if name == "result":
                raise AttributeError("simulate missing attribute")
            return super().__getattribute__(name)

    o = SotaSubmit()
    # put result into __dict__ so except branch can fetch it
    o.__dict__["result"] = result_df
    return o


def test_get_summary_df_full(tmp_path, monkeypatch):
    # Prepare summary.pkl
    summary_path = tmp_path / "summary.pkl"

    # Base summary dict for one experiment
    key = "exp1"
    competition_id = "comp_123"
    summary_dict = {
        key: {
            "loop_num": 3,
            "competition": competition_id,
            "success_loop_num": 2,
            "made_submission_num": 1,
            "valid_submission_num": 1,
            "above_median_num": 0,
            "bronze_num": 0,
            "silver_num": 0,
            "gold_num": 0,
            "get_medal_num": 0,
            "bronze_threshold": 0.0,  # will cause compare_score exception (division by zero)
            "silver_threshold": 0.5,
            "gold_threshold": 1.0,
            "median_threshold": 0.4,
            # sota keys will be overwritten by get_sota_exp_stat
        }
    }
    pd.to_pickle(summary_dict, summary_path)

    # Create stdout file so get_script_time is used
    stdout_file = tmp_path / f"{key}.stdout"
    stdout_file.write_text("dummy stdout")

    # Prepare times info: two loops with different step names and durations
    now = datetime.now()
    times_info = {
        "loop0": {
            "exp_gen": {"start_time": now, "end_time": now + timedelta(seconds=2)},
            "coding": {"start_time": now + timedelta(seconds=2), "end_time": now + timedelta(seconds=5)},
        },
        "loop1": {
            "running": {"start_time": now + timedelta(seconds=5), "end_time": now + timedelta(seconds=10)},
        },
    }

    # Monkeypatch functions used inside get_summary_df
    monkeypatch.setattr(utils, "get_script_time", lambda p: "00:00:01")
    monkeypatch.setattr(utils, "load_times_info", lambda p: times_info)

    # Prepare sota submit object whose .result raises AttributeError but available in __dict__
    # Make the result DataFrame have 'ensemble' index and string value to trigger string replacement branch
    submit_result_df = pd.DataFrame({"score": ["1"]}, index=["ensemble"])
    sota_submit_obj = make_sota_submit_obj(submit_result_df)

    # Define fake get_sota_exp_stat to return different results for selectors
    def fake_get_sota_exp_stat(path, selector="auto"):
        if selector == "auto":
            # return (sota_exp_submit, sota_loop_id_new, sota_submit_report, sota_exp_stat_new)
            return (
                sota_submit_obj,
                10,
                {"score": 2.0},  # sota_submit_report
                "sota_new",
            )
        else:
            # best_valid
            return (None, 9, {"score": 2.5}, "sota_old")

    monkeypatch.setattr(utils, "get_sota_exp_stat", fake_get_sota_exp_stat)

    # get_score_stat returns booleans and float
    monkeypatch.setattr(utils, "get_score_stat", lambda p, lid: (True, False, True, 0.75))

    # Create baseline CSV and point UI_SETTING to it
    baseline_csv = tmp_path / "baseline.csv"
    baseline_df = pd.DataFrame({"competition_id": [competition_id], "score": [1.0]})
    baseline_df.to_csv(baseline_csv, index=False)
    # Monkeypatch baseline path
    monkeypatch.setattr(ui_conf.UI_SETTING, "baseline_result_path", str(baseline_csv))

    # Call function
    summary_out, df = utils.get_summary_df(tmp_path)

    # Assertions on summary structure
    assert key in summary_out
    v = summary_out[key]
    # Exec times computed from times_info
    assert "exec_time" in v and isinstance(v["exec_time"], str)
    assert v["sota_loop_id_new"] == 10
    assert v["sota_loop_id"] == 9
    # sota_exp_score_new comes from fake_get_sota_exp_stat (auto) -> 2.0
    assert v["sota_exp_score_new"] == 2.0
    # sota_exp_score comes from best_valid -> 2.5
    assert v["sota_exp_score"] == 2.5
    # valid_improve from get_score_stat
    assert v["valid_improve"] is True
    assert v["merge_sota_rate"] == 0.75

    # Assertions on DataFrame contents
    assert competition_id == df.loc[key, "Competition"]
    assert int(df.loc[key, "Total Loops"]) == 3
    # According to code, valid_submission >0 sets Best Result to 'valid_submission'
    assert int(df.loc[key, "Made Submission"]) == 1
    assert int(df.loc[key, "Valid Submission"]) == 1
    assert df.loc[key, "Best Result"] == "valid_submission"

    # Baseline score present and numeric
    assert math.isclose(float(df.loc[key, "Baseline Score"]), 1.0)
    # Ours - Base = 2.5 - 1.0 = 1.5
    assert pytest.approx(float(df.loc[key, "Ours - Base"]), rel=1e-9) == 1.5
    # Ours vs Base should compute exp(abs(log(2.5/1.0))) = exp(ln2.5)
    expected_ours_vs_base = math.exp(abs(math.log(2.5 / 1.0)))
    assert pytest.approx(float(df.loc[key, "Ours vs Base"]), rel=1e-9) == expected_ours_vs_base

    # Ours vs Bronze should be None or NaN because bronze_threshold == 0 triggers exception in compare_score
    assert pd.isna(df.loc[key, "Ours vs Bronze"]) or df.loc[key, "Ours vs Bronze"] is None

    # SOTA Exp Score (valid, to_submit) came from submit_result_df's 'ensemble' value which was string '1'
    # Code replaces string entries in this column with 0.0
    assert float(df.loc[key, "SOTA Exp Score (valid, to_submit)"]) == 0.0

    # Types after astype: check numeric subdtype
    assert np.issubdtype(type(df.loc[key, "Total Loops"]), np.integer) or isinstance(int(df.loc[key, "Total Loops"]), int)
    assert np.issubdtype(type(df.loc[key, "Merge Sota"]), np.floating)
    # Ensure non-empty DataFrame
    assert not df.empty


def test_get_summary_df_no_summary(tmp_path):
    # When no summary.pkl exists, should return empty dict and empty DataFrame
    summary_out, df = utils.get_summary_df(tmp_path)
    assert summary_out == {}
    assert isinstance(df, pd.DataFrame)
    assert df.empty
