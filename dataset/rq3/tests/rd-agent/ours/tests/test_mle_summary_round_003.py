import json
from pathlib import Path
import builtins
import types

import pytest

import rdagent.log.mle_summary as mle_summary


class FakeMessage:
    def __init__(self, tag, content):
        self.tag = tag
        self.content = content


class FakeFileStorage:
    def __init__(self, path, messages):
        self._messages = messages

    def iter_msg(self):
        # return an iterator / list of messages
        return list(self._messages)


class DummyFBWorkspace:
    def __init__(self, execute_ret=None):
        self._execute_ret = execute_ret

    def execute(self, env=None, entry=None):
        # return a JSON string representing grade output thresholds
        if self._execute_ret is not None:
            return json.dumps(self._execute_ret)
        return json.dumps({
            "bronze_threshold": 1.0,
            "silver_threshold": 2.0,
            "gold_threshold": 3.0,
            "median_threshold": 0.5,
        })


class DummyMLE:
    def __init__(self, env=None):
        self.env = env


class DummyDSExperiment:
    def __init__(self, result=None):
        self.result = result


class DummyExperimentFeedback:
    def __init__(self, ok=True):
        self._ok = ok

    def __bool__(self):
        return bool(self._ok)


def _make_msgs_competition_running_feedback():
    # messages exercise competition -> FBWorkspace -> thresholds
    # running with DSExperiment -> valid_scores
    # running mle_score -> grade_output -> increments counters
    # feedback -> uses grade_output to set sota_exp_stat and score
    msgs = []
    # should be skipped because contains 'llm'
    msgs.append(FakeMessage("some_llm_tag", "ignored"))
    # competition message (no loop id)
    msgs.append(FakeMessage("competition", "comp-id-xyz"))
    # running DSExperiment with loop id '1'
    msgs.append(FakeMessage("running_ds", DummyDSExperiment(result=99)))
    # running mle_score with loop id '2'
    grade_output = {
        "submission_exists": True,
        "score": 42,
        "valid_submission": True,
        "above_median": True,
        "any_medal": True,
        "bronze_medal": False,
        "silver_medal": True,
        "gold_medal": False,
    }
    msgs.append(FakeMessage("running_mle_score", json.dumps(grade_output)))
    # feedback for loop id '2'
    msgs.append(FakeMessage("feedback", DummyExperimentFeedback(ok=True)))
    return msgs, grade_output


def _extract_loopid_func_name(tag):
    # returns (loop_id, fn) pair based on tag content
    if tag == "competition":
        return (None, None)
    if tag == "running_ds":
        return ("1", "run_ds")
    if tag == "running_mle_score":
        return ("2", "run_mle")
    if tag == "feedback":
        return ("2", "run_mle")
    # messages with llm should be skipped but still return an id
    if "llm" in tag:
        return ("3", "llm_fn")
    return (None, None)


def test_summarize_folder_competition_running_feedback_round_003(tmp_path, monkeypatch):
    # Arrange
    # prepare a fake log folder with one trace directory
    trace_dir = tmp_path / "trace1"
    trace_dir.mkdir()

    msgs, grade_output = _make_msgs_competition_running_feedback()

    # Patch FileStorage to return our messages for the trace
    def fake_filestorage_constructor(path):
        # ensure the path passed is the trace dir we expect
        assert Path(path).name in {trace_dir.name}
        return FakeFileStorage(path, msgs)

    monkeypatch.setattr(mle_summary, "FileStorage", fake_filestorage_constructor)

    # Patch extract_loopid_func_name
    monkeypatch.setattr(mle_summary, "extract_loopid_func_name", _extract_loopid_func_name)

    # Patch is_valid_session to allow the trace dir
    monkeypatch.setattr(mle_summary, "is_valid_session", lambda p: True)

    # Patch get_test_eval and MLETestEval so isinstance(...) is True and env attribute exists
    monkeypatch.setattr(mle_summary, "MLETestEval", DummyMLE)
    monkeypatch.setattr(mle_summary, "get_test_eval", lambda: DummyMLE(env="env-x"))

    # Patch FBWorkspace to return thresholds when execute is called
    fb_ws = DummyFBWorkspace(execute_ret={
        "bronze_threshold": 0.1,
        "silver_threshold": 0.2,
        "gold_threshold": 0.3,
        "median_threshold": 0.15,
    })

    monkeypatch.setattr(mle_summary, "FBWorkspace", lambda: fb_ws)

    # Patch extract_json to parse JSON strings to dicts
    monkeypatch.setattr(mle_summary, "extract_json", lambda s: json.loads(s) if isinstance(s, str) else s)

    # Patch DSExperiment and ExperimentFeedback classes for isinstance checks
    monkeypatch.setattr(mle_summary, "DSExperiment", DummyDSExperiment)
    monkeypatch.setattr(mle_summary, "ExperimentFeedback", DummyExperimentFeedback)

    # Capture pd.to_pickle arguments
    pk_calls = []

    def fake_to_pickle(obj, path):
        pk_calls.append((obj, Path(path)))

    monkeypatch.setattr(mle_summary.pd, "to_pickle", fake_to_pickle)

    # Act
    mle_summary.summarize_folder(str(tmp_path), hours=None)

    # Assert
    # Ensure pd.to_pickle was called once
    assert len(pk_calls) == 1
    stat_obj, saved_path = pk_calls[0]
    # The stat dict should contain an entry for our trace directory
    assert trace_dir.name in stat_obj
    entry = stat_obj[trace_dir.name]

    # Check counters were updated according to our grade_output
    assert entry["made_submission_num"] == 1
    assert entry["valid_submission_num"] == 1
    assert entry["above_median_num"] == 1
    assert entry["get_medal_num"] == 1
    assert entry["silver_num"] == 1
    assert entry["bronze_num"] == 0
    assert entry["gold_num"] == 0

    # Check test_scores and valid_scores mapping by loop id
    # loop ids were converted to ints inside summarize_folder: '2' -> 2 and '1' -> 1
    assert entry["test_scores"][2] == 42
    assert entry["valid_scores"][1] == 99

    # Check success loop and sota mapping from feedback
    assert entry["success_loop_num"] == 1
    assert entry["sota_exp_stat"] == "silver"
    assert entry["sota_exp_score"] == 42

    # Check thresholds were picked up from FBWorkspace.execute
    assert entry["bronze_threshold"] == pytest.approx(0.1)
    assert entry["silver_threshold"] == pytest.approx(0.2)
    assert entry["gold_threshold"] == pytest.approx(0.3)
    assert entry["median_threshold"] == pytest.approx(0.15)


def test_summarize_folder_hours_and_existing_save_removed_round_003(tmp_path, monkeypatch, capsys):
    # Arrange
    # Prepare a different trace directory
    trace_dir = tmp_path / "trace2"
    trace_dir.mkdir()

    # make a summary file that should be removed
    hours = 3
    save_name = f"summary_{hours}h.pkl"
    save_path = tmp_path / save_name
    save_path.write_text("old")
    assert save_path.exists()

    # Patch is_valid_session so the trace is processed
    monkeypatch.setattr(mle_summary, "is_valid_session", lambda p: True)

    # Make FileStorage return an iterator with a single message that will trigger the hours stop
    stop_msg = FakeMessage("running_stop", "nope")

    def fake_filestorage_constructor(path):
        return FakeFileStorage(path, [stop_msg])

    monkeypatch.setattr(mle_summary, "FileStorage", fake_filestorage_constructor)

    # Make extract_loopid_func_name return stop loop and fn for our message
    monkeypatch.setattr(mle_summary, "extract_loopid_func_name", lambda tag: ("5", "stop_fn") if tag == "running_stop" else (None, None))

    # Patch _get_loop_and_fn_after_hours to return the stop pair that matches the message
    monkeypatch.setattr(mle_summary, "_get_loop_and_fn_after_hours", lambda path, hrs: (5, "stop_fn"))

    # capture to_pickle calls but do not actually write
    pk_calls = []

    def fake_to_pickle(obj, path):
        pk_calls.append((obj, Path(path)))

    monkeypatch.setattr(mle_summary.pd, "to_pickle", fake_to_pickle)

    # Act
    mle_summary.summarize_folder(str(tmp_path), hours=hours)

    # Assert
    # Old file should have been removed by the function
    # The function prints when it removes the old file
    captured = capsys.readouterr()
    assert f"Old {save_name} removed." in captured.out

    # to_pickle should still have been called
    assert len(pk_calls) == 1
    stat_obj, saved_path = pk_calls[0]
    assert saved_path.name == save_name
    # even with break, stat should have an entry for the trace directory
    assert trace_dir.name in stat_obj
