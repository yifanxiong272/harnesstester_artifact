import types
import builtins
from types import SimpleNamespace
import pandas as pd
import importlib

import pytest

MODULE_PATH = "rdagent.components.coder.data_science.pipeline.eval"


def _import_mod():
    return importlib.import_module(MODULE_PATH)


class FakeTask:
    def __init__(self, info):
        self._info = info

    def get_task_information(self):
        return self._info


class FakeResult:
    def __init__(self, exit_code=0, stdout_text=""):
        self.exit_code = exit_code
        self._stdout = stdout_text

    def get_truncated_stdout(self):
        return self._stdout


class FakePathLike:
    def __init__(self, files=None):
        # files: dict filename->content
        self._files = files or {}
        self._name = "workspace"

    def __truediv__(self, other):
        # return a new FakePathLike representing the file
        child = FakePathLike(self._files)
        child._name = other
        return child

    def exists(self):
        return self._name in self._files

    def read_text(self):
        return self._files.get(self._name, "")

    def __fspath__(self):
        # not used by our monkeypatched pd.read_csv, but present
        return self._name


class DummyImplementation:
    def __init__(self, files=None, file_dict=None):
        self.file_dict = file_dict or {}
        self.workspace_path = FakePathLike(files)

    def execute(self, env=None, entry=None):
        # no-op for tests
        return None

    def run(self, env=None, entry=None):
        # return a default result; can be overridden in tests by replacing this method
        return FakeResult(exit_code=0, stdout_text="")


def _make_evaluator_and_defaults(monkeypatch, module):
    # Create evaluator instance without calling real constructor
    evaluator = object.__new__(module.PipelineCoSTEEREvaluator)

    # Minimal scen object expected by evaluate
    scen = SimpleNamespace(
        debug_path="debug_path",
        real_debug_timeout=lambda: 5,
        competition="comp",
        metric_name="Metric",
        get_scenario_all_desc=lambda eda_output=None: "scenario-desc",
    )
    evaluator.scen = scen

    # Patch helpers used in evaluate to deterministic fakes
    monkeypatch.setattr(module, "get_ds_env", lambda **kw: SimpleNamespace(conf=SimpleNamespace(running_timeout_period=10)))
    monkeypatch.setattr(module, "get_clear_ws_cmd", lambda: "clear_cmd")

    # T template object: return object with r() method producing a stable string
    monkeypatch.setattr(module, "T", lambda *a, **k: SimpleNamespace(r=lambda *aa, **kk: "templ"))

    return evaluator


def test_queried_success_and_failed_task_branches_round_002(monkeypatch):
    """
    Covers early-return when queried_knowledge contains success mapping (lines ~134-140)
    and the failed_task_info_set branch (lines ~140-148).
    """
    module = _import_mod()

    # Prepare evaluator and task
    evaluator = _make_evaluator_and_defaults(monkeypatch, module)

    # 1) Success mapping case: the function should return the provided feedback object directly
    target_task = FakeTask("task-success")

    queried_knowledge = SimpleNamespace(
        success_task_to_knowledge_dict={
            "task-success": SimpleNamespace(feedback="SENTINEL_FEEDBACK")
        },
        failed_task_info_set=set(),
    )

    res = module.PipelineCoSTEEREvaluator.evaluate(evaluator, target_task, implementation=None, gt_implementation=None, queried_knowledge=queried_knowledge)
    assert res == "SENTINEL_FEEDBACK"

    # 2) Failed task info set case: should return an object constructed in the function
    target_task2 = FakeTask("task-failed")
    queried_knowledge2 = SimpleNamespace(success_task_to_knowledge_dict={}, failed_task_info_set={"task-failed"})

    res2 = module.PipelineCoSTEEREvaluator.evaluate(evaluator, target_task2, implementation=None, gt_implementation=None, queried_knowledge=queried_knowledge2)

    # The returned object is constructed with fields including final_decision False
    # and textual fields indicating skip. We assert on the key properties.
    assert hasattr(res2, "final_decision")
    assert res2.final_decision is False
    # Should contain the skip message in code or error_message
    assert "skip implementation" in (getattr(res2, "error_message", "") or getattr(res2, "code", "") or "")


def test_sample_submission_triggers_rejection_round_002(monkeypatch):
    """
    Cover path where: no notebook conversion, sample_submission file is detected as opened (trace.log contains openat lines),
    scores.csv exists and passes checks (so score_ret_code stays 0), and therefore the sample submission check flips final_decision.
    This exercises: trace.log parsing (lines ~190-199), score file handling (219-246), and the final decision change for sample submission (340-344).
    """
    module = _import_mod()

    evaluator = _make_evaluator_and_defaults(monkeypatch, module)

    # Prepare DS_RD_SETTING flags deterministically
    monkeypatch.setattr(module, "DS_RD_SETTING", SimpleNamespace(sample_data_by_LLM=False, enable_notebook_conversion=False, enable_mcp_documentation_search=True))

    # Fake get_test_eval with deterministic behavior
    class FakeTestEval:
        def get_sample_submission_name(self, competition):
            return "sample.csv"

        def is_sub_enabled(self, competition):
            # used to choose not to run submission check (we return False so submission_ret_code = 0)
            return False

        def enabled(self, competition):
            return False

        def valid(self, competition, implementation):
            return ("OK", 0)

    monkeypatch.setattr(module, "get_test_eval", lambda: FakeTestEval())

    # Build a fake implementation that looks like FBWorkspace
    trace_content = "something openat ... sample.csv ... openat ..."
    files = {"trace.log": trace_content, "scores.csv": "dummy"}
    impl = DummyImplementation(files=files, file_dict={"main.py": "print(1)", "EDA.md": "EDA CONTENT"})

    # Ensure module recognizes our implementation as FBWorkspace for eda_output extraction
    monkeypatch.setattr(module, "FBWorkspace", DummyImplementation)

    # Make run return non-error exit code but some stdout (we want score checks to run)
    def run_ok(env=None, entry=None):
        return FakeResult(exit_code=0, stdout_text="run output")

    impl.run = run_ok

    # monkeypatch pd.read_csv used in the code to return a DataFrame with proper index and column
    def fake_read_csv(fp, index_col=0):
        # return a DataFrame with unique index including 'ensemble' and a single column named evaluator.scen.metric_name
        df = pd.DataFrame({"Metric": [0.5]}, index=["ensemble"])
        df.index.name = None
        return df

    monkeypatch.setattr(module, "pd", SimpleNamespace(read_csv=fake_read_csv))

    # Build wfb object returned by build_cls_from_json_with_retry
    # start as an object with final_decision True so it can be flipped by sample_submission_check
    wfb = SimpleNamespace(final_decision=True, return_checking="", requires_documentation_search=False, error_message="")

    monkeypatch.setattr(module, "build_cls_from_json_with_retry", lambda *a, **k: wfb)

    # Force DocAgent to not be called / harmless if called
    class DummyDocAgent:
        def query(self, query=None):
            return None

    monkeypatch.setattr(module, "DocAgent", DummyDocAgent)

    # Prepare a target task that is not in any queried_knowledge
    target_task = FakeTask("task-x")

    # Call evaluate: with the prepared environment the code should detect sample submission open and flip decision
    res = module.PipelineCoSTEEREvaluator.evaluate(evaluator, target_task, implementation=impl, gt_implementation=None, queried_knowledge=None)

    # After the evaluation, because trace.log contains an openat to sample.csv, sample_submission_check becomes False
    # and since wfb.final_decision started True, it should be set to False and return_checking should contain the sample submission message
    assert hasattr(res, "final_decision")
    assert res.final_decision is False
    assert "Sample submission file check failed" in res.return_checking or "sample submission" in res.return_checking.lower()
