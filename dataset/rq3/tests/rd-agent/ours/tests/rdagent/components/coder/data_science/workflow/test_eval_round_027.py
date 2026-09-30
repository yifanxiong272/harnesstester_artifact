import json
from pathlib import Path
import pandas as pd
import re
import importlib
import types

import pytest

# Import the module under test
mod = importlib.import_module("rdagent.components.coder.data_science.workflow.eval")

# Helpers / fakes used across tests
class DummyTask:
    def __init__(self, info):
        self._info = info

    def get_task_information(self):
        return self._info


class DummyQueriedKnowledge:
    def __init__(self, success_map=None, failed_set=None):
        self.success_task_to_knowledge_dict = success_map or {}
        self.failed_task_info_set = failed_set or set()


class DummyFeedback:
    def __init__(self, **kwargs):
        # allow both direct value or keyword attributes
        self._raw = kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return f"DummyFeedback({self._raw})"


class DummySubmissionResult:
    def __init__(self, exit_code=0, stdout=""):
        self.exit_code = exit_code
        self._stdout = stdout

    def get_truncated_stdout(self):
        return self._stdout


class DummyImplementation:
    def __init__(self, workspace_path: Path, file_dict=None):
        self.workspace_path = workspace_path
        self.file_dict = file_dict or {}
        self.exec_calls = []
        self.injected = {}

    def execute(self, env, entry):
        # record calls and emulate a stdout string
        self.exec_calls.append((env, entry))
        return f"executed:{entry}"

    def inject_files(self, **kwargs):
        # mimic writing files into workspace
        for k, v in kwargs.items():
            # store file text in file_dict under path-like key
            self.file_dict[k] = v
            self.injected[k] = v

    def run(self, env, entry):
        # emulate running a submission check (test) script
        # return an object with get_truncated_stdout and exit_code
        # default success, unless injected special content indicates failure
        out = "ok"
        exit_code = 0
        return DummySubmissionResult(exit_code=exit_code, stdout=out)


# Build a WorkflowGeneralCaseSpecEvaluator instance without invoking its real constructor
def make_evaluator(monkeypatch, scen=None):
    EvaluatorCls = mod.WorkflowGeneralCaseSpecEvaluator
    ev = object.__new__(EvaluatorCls)
    # minimal scen with attributes used in evaluate
    class S:
        def __init__(self):
            self.debug_path = "debug_path"
            self.metric_name = "Accuracy"
        def real_debug_timeout(self):
            return 5
        def get_scenario_all_desc(self, eda_output=None):
            return {"desc": "scenario"}

    ev.scen = scen or S()
    return ev


# Patch common external dependencies in module to deterministic fakes
@pytest.fixture(autouse=True)
def patch_module_dependencies(monkeypatch, tmp_path):
    # get_ds_env: just return a dummy env object
    monkeypatch.setattr(mod, "get_ds_env", lambda **kwargs: object())
    # get_clear_ws_cmd: deterministic command
    monkeypatch.setattr(mod, "get_clear_ws_cmd", lambda: "clear_cmd")
    # remove_eda_part: identity function
    monkeypatch.setattr(mod, "remove_eda_part", lambda s: s)
    # T(...).r() used to produce small strings: make it return object with r() method
    class FakeT:
        def __init__(self, *a, **k):
            self.a = a
            self.k = k
        def r(self, *a, **k):
            return "fake_template"
    monkeypatch.setattr(mod, "T", FakeT)
    # build_cls_from_json_with_retry: return a DummyFeedback object; tests may override if needed
    def fake_builder(cls, **kwargs):
        # return an object with attributes expected later (final_decision, return_checking)
        obj = DummyFeedback(final_decision=True, return_checking="")
        return obj
    monkeypatch.setattr(mod, "build_cls_from_json_with_retry", fake_builder)
    # Ensure logger.info is harmless
    class DummyLogger:
        def info(self, *a, **k):
            pass
    monkeypatch.setattr(mod, "logger", DummyLogger())
    yield


def test_return_from_queried_success_round_027(monkeypatch):
    # Setup evaluator and inputs such that the success mapping short-circuits
    ev = make_evaluator(monkeypatch)
    t = DummyTask("task-ok")
    success_feedback = DummyFeedback(result="SUCCESS")
    qk = DummyQueriedKnowledge(success_map={"task-ok": types.SimpleNamespace(feedback=success_feedback)})

    # Call evaluate and assert the returned object is exactly the mapped feedback
    res = ev.evaluate(target_task=t, implementation=None, gt_implementation=None, queried_knowledge=qk)
    assert res is success_feedback


def test_return_from_queried_failed_round_027(monkeypatch):
    # Setup evaluator and inputs to trigger the failed_task_info_set branch
    ev = make_evaluator(monkeypatch)
    t = DummyTask("task-failed")
    qk = DummyQueriedKnowledge(failed_set={"task-failed"})

    # Patch WorkflowSingleFeedback in module to a simple stand-in that captures kwargs
    class WSFake:
        def __init__(self, **kwargs):
            # mimic attributes used later in evaluate
            self.execution = kwargs.get("execution")
            self.return_checking = kwargs.get("return_checking")
            self.code = kwargs.get("code")
            self.final_decision = kwargs.get("final_decision")
        def __repr__(self):
            return f"WSFake(final_decision={self.final_decision})"

    monkeypatch.setattr(mod, "WorkflowSingleFeedback", WSFake)

    res = ev.evaluate(target_task=t, implementation=None, gt_implementation=None, queried_knowledge=qk)
    # Expect a WorkflowSingleFeedback-like object with final_decision False
    assert isinstance(res, WSFake)
    assert res.final_decision is False
    assert "skip implementation" in res.execution


def test_score_missing_with_single_coverage_file_round_027(tmp_path, monkeypatch):
    # Setup workspace with no scores.csv but with coverage.json containing a single file
    ws_dir = tmp_path / "ws1"
    ws_dir.mkdir()
    coverage_path = ws_dir / "coverage.json"
    coverage_path.write_text(json.dumps({"files": {"only.py": {}}}))

    impl = DummyImplementation(workspace_path=ws_dir, file_dict={"main.py": "print('hi')"})

    # Ensure implementation.execute does not delete our coverage.json and is callable
    ev = make_evaluator(monkeypatch)

    # Patch build to return a feedback object we can inspect
    def fake_builder(cls, **kwargs):
        return DummyFeedback(final_decision=True, return_checking="orig")

    monkeypatch.setattr(mod, "build_cls_from_json_with_retry", fake_builder)

    # No scores.csv -> branch that sets score_ret_code=1 and checks coverage.json files
    res = ev.evaluate(target_task=DummyTask("t_missing_score"), implementation=impl, gt_implementation=None, queried_knowledge=None)

    # Expect returned object to have final_decision set to False and message about missing metrics
    assert hasattr(res, "final_decision")
    assert res.final_decision is False
    assert "Metrics file" in res.return_checking or "Metrics file" in getattr(res, "return_checking", "")
    # Because coverage.json contained a single file, the special hint should be present
    assert "The only used script" in res.return_checking


def test_score_checks_mismatch_round_027(tmp_path, monkeypatch):
    # Create a workspace with a scores.csv that will fail index, column and NaN checks
    ws_dir = tmp_path / "ws2"
    ws_dir.mkdir()

    # Craft a DataFrame: index names that do not match model files, wrong column name, and a NaN value
    df = pd.DataFrame({"WrongMetric": [1.0, None]}, index=["model_x", "model_y"])
    scores_path = ws_dir / "scores.csv"
    df.to_csv(scores_path)

    # Create implementation with file_dict containing only a single model file 'model_a.py' so model_set_in_folder={'model_a'}
    impl = DummyImplementation(workspace_path=ws_dir, file_dict={"model_a.py": "# code", "main.py": "print('x')", "spec/workflow.md": "spec"})

    # Ensure inject_files stores the injected test file into file_dict (done by DummyImplementation)

    # Patch build_cls_from_json_with_retry to return a feedback object we can inspect
    def fake_builder(cls, **kwargs):
        return DummyFeedback(final_decision=True, return_checking="start")

    monkeypatch.setattr(mod, "build_cls_from_json_with_retry", fake_builder)

    # Evaluate
    ev = make_evaluator(monkeypatch)
    res = ev.evaluate(target_task=DummyTask("t_scores"), implementation=impl, gt_implementation=None, queried_knowledge=None)

    # Result should have final_decision False due to score checks failing
    assert hasattr(res, "final_decision")
    assert res.final_decision is False
    # The return_checking should include messages about model names and columns and NaN
    rc = res.return_checking
    assert "scores dataframe does not contain the correct model names" in rc or "scores dataframe" in rc
    assert "does not contain the correct column names" in rc or "Correct columns" in rc
    assert "contains NaN values" in rc or "NaN" in rc
