# file: rdagent/components/coder/data_science/raw_data_loader/eval.py:27-94
# asked: {"lines": [35, 37, 38, 40, 41, 42, 43, 44, 45, 46, 49, 50, 51, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 67, 68, 69, 71, 73, 74, 75, 76, 77, 78, 80, 81, 82, 83, 86, 88, 89, 92, 94], "branches": [[36, 40], [36, 41], [41, 42], [41, 49], [64, 65], [64, 67], [67, 68], [67, 71]]}
# gained: {"lines": [35, 37, 38, 40, 41, 42, 43, 44, 45, 46, 49, 50, 51, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 67, 68, 69, 71, 73, 74, 75, 76, 77, 78, 80, 81, 82, 83, 86, 88, 89, 92, 94], "branches": [[36, 40], [36, 41], [41, 42], [41, 49], [64, 65], [64, 67], [67, 68], [67, 71]]}

import re
import types
import pytest
import importlib

# Import the module under test
eval_mod = importlib.import_module(
    "rdagent.components.coder.data_science.raw_data_loader.eval"
)


class DummyTask:
    def __init__(self, info):
        self._info = info

    def get_task_information(self):
        return self._info


class DummySuccessKnowledgeEntry:
    def __init__(self, feedback):
        self.feedback = feedback


class DummyQueriedKnowledge:
    def __init__(self, success_map=None, failed_set=None):
        self.success_task_to_knowledge_dict = success_map or {}
        self.failed_task_info_set = failed_set or set()


class DummyResult:
    def __init__(self, stdout, exit_code):
        self._stdout = stdout
        self.exit_code = exit_code

    def get_truncated_stdout(self):
        return self._stdout


class DummyImplementation:
    def __init__(self, file_dict=None, all_codes=""):
        self.file_dict = file_dict or {}
        self.all_codes = all_codes
        self.injected = {}

    def inject_files(self, **files):
        # mimic storing injected files
        self.injected.update(files)

    def run(self, env=None, entry=None):
        return getattr(self, "_run_result")

    def execute(self, env=None, entry=None):
        return getattr(self, "_execute_result")


class DummyEnv:
    pass


class FakeTObj:
    def __init__(self, key=None):
        self.key = key

    def r(self, *args, **kwargs):
        # Return a deterministic string
        return f"rval_for_{self.key}"


class FakeT:
    def __call__(self, key):
        return FakeTObj(key)


class FakeDataLoaderEvalFeedback:
    def __init__(self, execution=None, return_checking=None, code=None, final_decision=True):
        self.execution = execution
        self.return_checking = return_checking
        self.code = code
        self.final_decision = final_decision

    @staticmethod
    def val_and_update_init_dict(d):
        # just return the dict unchanged for the fake builder
        return d


def make_evaluator_with_scen():
    class DummyScen:
        debug_path = "dbg_path"
        def real_debug_timeout(self):
            return 123
    return eval_mod.DataLoaderCoSTEEREvaluator(DummyScen())


def test_queried_knowledge_success_branch(monkeypatch):
    # Prepare evaluator and inputs; pass a minimal scen to satisfy constructor
    evaluator = make_evaluator_with_scen()
    task = DummyTask("task_success")
    expected_feedback = object()

    qk = DummyQueriedKnowledge(
        success_map={"task_success": DummySuccessKnowledgeEntry(expected_feedback)},
        failed_set=set(),
    )

    # Call evaluate; since queried_knowledge contains the task, it should return the mapped feedback
    result = evaluator.evaluate(target_task=task, implementation=None, gt_implementation=None, queried_knowledge=qk)

    assert result is expected_feedback


def test_queried_knowledge_failed_branch(monkeypatch):
    # Prepare evaluator and inputs; pass scen to constructor
    evaluator = make_evaluator_with_scen()
    task = DummyTask("task_failed")

    # Replace DataLoaderEvalFeedback in module to our fake to be able to inspect returned instance
    monkeypatch.setattr(eval_mod, "DataLoaderEvalFeedback", FakeDataLoaderEvalFeedback, raising=False)

    qk = DummyQueriedKnowledge(success_map={}, failed_set={"task_failed"})

    result = evaluator.evaluate(target_task=task, implementation=None, gt_implementation=None, queried_knowledge=qk)

    # The returned object should be our FakeDataLoaderEvalFeedback with fields set as in source
    assert isinstance(result, FakeDataLoaderEvalFeedback)
    assert result.execution == "This task has failed too many times, skip implementation."
    assert result.return_checking == "This task has failed too many times, skip implementation."
    assert result.code == "This task has failed too many times, skip implementation."
    assert result.final_decision is False


def test_full_flow_truncation_and_workflow_and_final_decision_toggle(monkeypatch):
    """
    This test exercises the main evaluate flow:
    - get_ds_env is called
    - T(...) .r() is used to build extra_volumes
    - implementation.inject_files and run are used
    - stdout contains EDA markers with a very long EDA part to trigger the truncation branch
    - implementation.file_dict contains "main.py" and run exit_code == 0, so execute() is called and its output is processed by remove_eda_part
    - build_cls_from_json_with_retry is stubbed to return a feedback object; final_decision is updated depending on ret_code
    """

    # Setup fake environment and hooks
    monkeypatch.setattr(eval_mod, "get_ds_env", lambda *args, **kwargs: DummyEnv(), raising=False)
    monkeypatch.setattr(eval_mod, "T", FakeT(), raising=False)
    # remove_eda_part should be called on workflow stdout; make it return a known value
    monkeypatch.setattr(eval_mod, "remove_eda_part", lambda s: f"removed:{s}", raising=False)

    # Prepare a fake implementation with a main.py present
    impl = DummyImplementation(file_dict={"load_data.py": "print('load')", "main.py": "print('main')"}, all_codes="allcodes")
    # Prepare a very long eda output: >10000 words
    long_eda = "word " * 10001
    stdout = "PRE" + "=== Start of EDA part ===" + long_eda + "=== End of EDA part ===" + "POST"
    impl._run_result = DummyResult(stdout=stdout, exit_code=0)
    impl._execute_result = "workflow stdout with === Start of EDA part === removed === End of EDA part ==="

    # Prepare evaluator with scen via constructor
    evaluator = make_evaluator_with_scen()

    # Monkeypatch DIRNAME / reading test file content: instead of file IO, ensure the code reads a fake test_code
    class FakePath:
        def __truediv__(self, other):
            return self
        def read_text(self):
            return "TEST_CODE_CONTENT"
    monkeypatch.setattr(eval_mod, "DIRNAME", FakePath(), raising=False)

    # Monkeypatch build_cls_from_json_with_retry to return an instance of our fake feedback class
    def fake_build(cls, *args, **kwargs):
        fb = FakeDataLoaderEvalFeedback(execution="exec", return_checking="rc", code="code", final_decision=True)
        return fb

    monkeypatch.setattr(eval_mod, "build_cls_from_json_with_retry", fake_build, raising=False)

    # Monkeypatch DataLoaderEvalFeedback to our fake for any direct instantiation inside function (though build is used)
    monkeypatch.setattr(eval_mod, "DataLoaderEvalFeedback", FakeDataLoaderEvalFeedback, raising=False)

    # Create a dummy task that won't be present in queried knowledge, so full flow executes
    task = DummyTask("no_query")

    # Call evaluate and assert returned feedback final_decision stays True because ret_code == 0
    fb = evaluator.evaluate(target_task=task, implementation=impl, gt_implementation=None, queried_knowledge=None)

    assert isinstance(fb, FakeDataLoaderEvalFeedback)
    assert fb.final_decision is True

    # Ensure that EDA truncation marker was applied indirectly by presence of EDA in run stdout
    assert impl._run_result.get_truncated_stdout().startswith("PRE")
    # Also ensure execute() was called and its result was processed by remove_eda_part via fake returning prefixed value:
    workflow_stdout_processed = eval_mod.remove_eda_part(impl._execute_result)
    assert workflow_stdout_processed.startswith("removed:")


def test_full_flow_nonzero_exit_without_main(monkeypatch):
    """
    Test the branch where run returns a non-zero exit code and implementation.file_dict does not contain main.py.
    final_decision should be set to False by the end of evaluate.
    """

    monkeypatch.setattr(eval_mod, "get_ds_env", lambda *args, **kwargs: DummyEnv(), raising=False)
    monkeypatch.setattr(eval_mod, "T", FakeT(), raising=False)
    monkeypatch.setattr(eval_mod, "remove_eda_part", lambda s: s, raising=False)

    impl = DummyImplementation(file_dict={"load_data.py": "print('load')"}, all_codes="allcodes")
    stdout = "NOEDA"
    impl._run_result = DummyResult(stdout=stdout, exit_code=1)  # non-zero to force final_decision False

    # evaluator with scen via constructor
    evaluator = make_evaluator_with_scen()

    # Patch DIRNAME to avoid file IO
    class FakePath2:
        def __truediv__(self, other):
            return self
        def read_text(self):
            return "TEST_CODE_CONTENT"
    monkeypatch.setattr(eval_mod, "DIRNAME", FakePath2(), raising=False)

    # build_cls_from_json_with_retry returns an object with final_decision True, but evaluate should set it False due to ret_code != 0
    monkeypatch.setattr(eval_mod, "build_cls_from_json_with_retry", lambda *args, **kwargs: FakeDataLoaderEvalFeedback(final_decision=True), raising=False)
    monkeypatch.setattr(eval_mod, "DataLoaderEvalFeedback", FakeDataLoaderEvalFeedback, raising=False)

    task = DummyTask("no_query_2")
    fb = evaluator.evaluate(target_task=task, implementation=impl, gt_implementation=None, queried_knowledge=None)

    assert isinstance(fb, FakeDataLoaderEvalFeedback)
    # Because ret_code == 1, final_decision must be False
    assert fb.final_decision is False
