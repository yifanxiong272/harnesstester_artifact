import json
import importlib
from types import SimpleNamespace
from pathlib import Path
import pytest

# Import the module under test
eval_mod = importlib.import_module("rdagent.components.coder.data_science.workflow.eval")
WorkflowGeneralCaseSpecEvaluator = eval_mod.WorkflowGeneralCaseSpecEvaluator
WorkflowSingleFeedback = getattr(eval_mod, "WorkflowSingleFeedback", SimpleNamespace)

# Helpers / fakes used by tests
class FakeTask:
    def __init__(self, info):
        self._info = info

    def get_task_information(self):
        return self._info

class FakeQueriedKnowledge:
    def __init__(self, success_dict=None, failed_set=None):
        self.success_task_to_knowledge_dict = success_dict or {}
        self.failed_task_info_set = failed_set or set()

class FakeKnowledgeValue:
    def __init__(self, feedback):
        self.feedback = feedback

class FakeWorkspace:
    def __init__(self, workspace_path: Path, file_dict: dict):
        self.workspace_path = workspace_path
        self.file_dict = dict(file_dict)

    def execute(self, env=None, entry=None):
        # Simulate producing coverage.json when coverage json command is requested
        if entry and "coverage json" in entry:
            cov_path = self.workspace_path / "coverage.json"
            cov_path.write_text(json.dumps({"files": {"only.py": {}}}))
            return "coverage json produced"
        # Simulate running main with coverage
        if entry and "coverage run main.py" in entry:
            return "main run stdout"
        # Clear workspace command or other commands: do nothing
        return ""

    def inject_files(self, **kwargs):
        # simulate injecting files into workspace file dict
        for k, v in kwargs.items():
            self.file_dict[k] = v

    def run(self, env=None, entry=None):
        # Simulate running submission test: return an object with get_truncated_stdout and exit_code
        class Result:
            def __init__(self, out, exit_code=0):
                self._out = out
                self.exit_code = exit_code

            def get_truncated_stdout(self):
                return self._out

        return Result("submission test stdout", exit_code=0)

# Dummy T factory used by the module: T(...).r(...) -> returns predictable strings
class DummyT:
    def __init__(self, *args, **kwargs):
        pass

    def r(self, *a, **kw):
        # Return a short predictable content used for prompts and injection
        return "DUMMY_R"


def make_evaluator_minimal():
    # Create an evaluator instance without invoking heavy initialization
    ev = object.__new__(WorkflowGeneralCaseSpecEvaluator)
    return ev


def setup_basic_monkeypatches(monkeypatch, tmp_path: Path):
    # Replace environment / utilities used by evaluate with deterministic fakes
    monkeypatch.setattr(eval_mod, "get_ds_env", lambda **kwargs: "FAKE_ENV")
    monkeypatch.setattr(eval_mod, "remove_eda_part", lambda s: s)
    monkeypatch.setattr(eval_mod, "T", DummyT)
    # Ensure DS_RD_SETTING exists and set spec_enabled to False for deterministic branch
    try:
        monkeypatch.setattr(eval_mod.DS_RD_SETTING, "spec_enabled", False)
    except Exception:
        # If DS_RD_SETTING is not settable, just ignore
        pass


def test_evaluate_returns_queried_feedback_round_028():
    """
    Cover early-return branch when queried_knowledge contains a success mapping.
    The evaluator should return the feedback object directly.
    """
    evaluator = make_evaluator_minimal()

    # Prepare a fake feedback object and ensure it is returned verbatim
    # NOTE: WorkflowSingleFeedback requires positional args (execution, return_checking, code).
    # Construct a valid instance with minimal required values so instantiation does not fail.
    if hasattr(eval_mod, "WorkflowSingleFeedback"):
        # provide minimal required constructor args; other code expects .final_decision and .return_checking
        try:
            sentinel_feedback = eval_mod.WorkflowSingleFeedback(
                execution="exec",
                return_checking="checking",
                code="code",
                final_decision=True,
            )
        except TypeError:
            # Fallback to a simple namespace if constructor signature differs
            sentinel_feedback = SimpleNamespace(execution="exec", return_checking="checking", code="code", final_decision=True)
    else:
        sentinel_feedback = SimpleNamespace(execution="exec", return_checking="checking", code="code", final_decision=True)

    fake_value = FakeKnowledgeValue(feedback=sentinel_feedback)

    task = FakeTask("task_info_1")
    qk = FakeQueriedKnowledge(success_dict={"task_info_1": fake_value})

    # Call evaluate; implementation and gt_implementation are not needed for early-return
    result = evaluator.evaluate(target_task=task, implementation=None, gt_implementation=None, queried_knowledge=qk)

    # Observable assertion: should be the exact feedback object from the queried knowledge
    assert result is sentinel_feedback


def test_evaluate_scores_missing_coverage_one_file_round_028(monkeypatch, tmp_path):
    """
    Simulate a run where scores.csv is missing; implementation.execute produces a coverage.json
    containing exactly one used file. This should trigger the branch that appends an error
    indicating the metrics file is not generated and mention the only used script.
    """
    setup_basic_monkeypatches(monkeypatch, tmp_path)

    # Prepare evaluator with minimal scenario used later
    evaluator = make_evaluator_minimal()

    # Minimal scen used by evaluate
    scen = SimpleNamespace()
    scen.debug_path = "some/debug/path"
    scen.real_debug_timeout = lambda: 1
    scen.metric_name = "Accuracy"
    scen.get_scenario_all_desc = lambda eda_output=None: "SCEN_DESC"
    evaluator.scen = scen

    # Prepare a fake workspace directory
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()

    # Provide a minimal set of files in file_dict including main.py
    file_dict = {"main.py": "print('hello')", "spec/workflow.md": "spec"}
    fw = FakeWorkspace(ws_dir, file_dict)

    # Ensure scores.csv does not exist so the missing-file branch is taken
    score_fp = ws_dir / "scores.csv"
    if score_fp.exists():
        score_fp.unlink()

    # Monkeypatch build_cls_from_json_with_retry to return an object we can inspect
    initial_wfb = SimpleNamespace(final_decision=True, return_checking="INIT_CHECK")
    monkeypatch.setattr(eval_mod, "build_cls_from_json_with_retry", lambda *a, **kw: initial_wfb)

    # Create a fake task; queried_knowledge is None to follow normal flow
    task = FakeTask("task_info_2")

    # Execute evaluate
    result_wfb = evaluator.evaluate(target_task=task, implementation=fw, gt_implementation=None, queried_knowledge=None)

    # Assertions: since scores.csv is missing, final_decision should be False and return_checking should contain our error
    assert result_wfb.final_decision is False
    assert "[Error] Metrics file (scores.csv) is not generated!" in result_wfb.return_checking
    # The coverage.json we produced had a single file 'only.py' so the message about the only used script should appear
    assert "The only used script is" in result_wfb.return_checking
    assert "only.py" in result_wfb.return_checking
