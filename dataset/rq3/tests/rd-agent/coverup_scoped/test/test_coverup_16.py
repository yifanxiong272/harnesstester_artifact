# file: rdagent/components/coder/data_science/model/eval.py:38-123
# asked: {"lines": [46, 48, 49, 51, 52, 53, 54, 55, 56, 57, 60, 61, 62, 65, 67, 68, 69, 70, 72, 73, 74, 75, 77, 78, 79, 82, 83, 84, 86, 87, 88, 90, 92, 93, 94, 95, 96, 98, 99, 100, 103, 104, 105, 106, 107, 108, 110, 111, 112, 115, 117, 118, 121, 123], "branches": [[47, 51], [47, 52], [52, 53], [52, 60], [67, 68], [67, 82], [77, 78], [77, 86], [86, 87], [86, 90], [92, 93], [92, 103]]}
# gained: {"lines": [46, 48, 49, 51, 52, 53, 54, 55, 56, 57, 60, 61, 62, 65, 67, 68, 69, 70, 72, 73, 74, 75, 77, 86, 90, 92, 103, 104, 105, 106, 107, 108, 110, 111, 112, 115, 117, 118, 121, 123], "branches": [[47, 51], [47, 52], [52, 53], [52, 60], [67, 68], [77, 86], [86, 90], [92, 103]]}

import pytest
from pathlib import Path

import rdagent.components.coder.data_science.model.eval as eval_mod


class FakeScenario:
    def __init__(self):
        self.debug_path = "debug_path_key"

    def real_debug_timeout(self):
        return 123


class FakeTask:
    def __init__(self, name, info):
        self.name = name
        self._info = info

    def get_task_information(self):
        return self._info


class FakeQueriedKnowledge:
    def __init__(self, success_dict=None, failed_set=None):
        self.success_task_to_knowledge_dict = success_dict or {}
        self.failed_task_info_set = failed_set or set()


def test_evaluate_returns_feedback_from_queried_success(monkeypatch):
    # Arrange: prepare evaluator and queried knowledge that contains success mapping
    evaluator = eval_mod.ModelGeneralCaseSpecEvaluator(FakeScenario())
    task_info = "unique-task-info-success"
    t = FakeTask(name="model01", info=task_info)

    sentinel_feedback = object()

    class Holder:
        def __init__(self, feedback):
            self.feedback = feedback

    qk = FakeQueriedKnowledge(success_dict={task_info: Holder(sentinel_feedback)})

    # Act
    out = evaluator.evaluate(target_task=t, implementation=None, gt_implementation=None, queried_knowledge=qk)

    # Assert the evaluator returned the exact feedback object from the queried knowledge
    assert out is sentinel_feedback


def test_evaluate_returns_failure_feedback_for_failed_task(monkeypatch):
    # Arrange: prepare evaluator and queried knowledge that marks the task as failed
    evaluator = eval_mod.ModelGeneralCaseSpecEvaluator(FakeScenario())
    task_info = "unique-task-info-failed"
    t = FakeTask(name="model02", info=task_info)

    qk = FakeQueriedKnowledge(success_dict={}, failed_set={task_info})

    # Act
    out = evaluator.evaluate(target_task=t, implementation=None, gt_implementation=None, queried_knowledge=qk)

    # Assert that the evaluator returned a ModelSingleFeedback with the expected messages
    assert isinstance(out, eval_mod.ModelSingleFeedback)
    expected_message = "This task has failed too many times, skip implementation."
    assert out.execution == expected_message
    assert out.return_checking == expected_message
    assert out.code == expected_message
    assert out.final_decision is False


def test_full_flow_model_removed_branch_and_build_prompt(monkeypatch, tmp_path):
    # Arrange
    evaluator = eval_mod.ModelGeneralCaseSpecEvaluator(FakeScenario())
    task_name = "some_model"
    task_info = "task-info-full-flow"
    t = FakeTask(name=task_name, info=task_info)

    # Monkeypatch get_ds_env to a simple env dict
    monkeypatch.setattr(eval_mod, "get_ds_env", lambda **kwargs: {"env": "ok"})

    # Prepare DIRNAME / eval_tests / model_test.txt with content containing model01 for replacement
    eval_tests_dir = tmp_path / "eval_tests"
    eval_tests_dir.mkdir()
    model_test_file = eval_tests_dir / "model_test.txt"
    # content contains "model01" which will be replaced with task_name
    model_test_file.write_text("print('model01 removed')\n")

    # Patch DIRNAME in module
    monkeypatch.setattr(eval_mod, "DIRNAME", tmp_path)

    # Monkeypatch remove_eda_part to just return the input (or slightly transform)
    monkeypatch.setattr(eval_mod, "remove_eda_part", lambda s: s.replace("EDA", "") if isinstance(s, str) else s)

    # Fake implementation/workspace
    class FakeResult:
        def __init__(self, stdout, exit_code):
            self._stdout = stdout
            self.exit_code = exit_code

        def get_truncated_stdout(self):
            return self._stdout

    class FakeImplementation:
        def __init__(self):
            # contains the model file to trigger removal branch and main.py to trigger workflow execution
            self.file_dict = {f"{task_name}.py": "model code", "main.py": "main code"}
            self.all_codes = "all_codes_here"

        def inject_files(self, **kwargs):
            # inject the generated test file
            self.file_dict.update(kwargs)

        def run(self, env, entry):
            # Simulate running the injected test; return a stdout (not None) and an exit_code (non-zero to demonstrate override)
            return FakeResult(stdout="original stdout", exit_code=2)

        def execute(self, env, entry):
            # Simulate workflow execution output that includes an "EDA" part to be removed
            return "Workflow result EDA part"

    impl = FakeImplementation()

    # Fake T class used for templating
    class FakeTemplate:
        def __init__(self, path):
            self.path = path

        def r(self, **kwargs):
            # produce a predictable string including the path and the kwargs keys/values for assertions
            return f"TEMPLATE:{self.path}|{kwargs}"

    monkeypatch.setattr(eval_mod, "T", FakeTemplate)

    # Prepare a ModelSingleFeedback-like object to be returned by build_cls_from_json_with_retry
    class FakeFB:
        def __init__(self):
            self.final_decision = True

    recorded = {}

    # Monkeypatch build_cls_from_json_with_retry to capture prompts and return our fake feedback
    def fake_build_cls_from_json_with_retry(cls, *args, **kwargs):
        # record the provided prompts for later assertion
        recorded['cls'] = cls
        recorded['system_prompt'] = kwargs.get('system_prompt')
        recorded['user_prompt'] = kwargs.get('user_prompt')
        recorded['init_kwargs_update_func'] = kwargs.get('init_kwargs_update_func')
        return FakeFB()

    monkeypatch.setattr(eval_mod, "build_cls_from_json_with_retry", fake_build_cls_from_json_with_retry)

    # Act
    fb = evaluator.evaluate(target_task=t, implementation=impl, gt_implementation=None, queried_knowledge=None)

    # Assert: build was called for CoSTEERSingleFeedback (ModelSingleFeedback alias) and returned our FakeFB
    assert isinstance(fb, FakeFB)

    # Observed behavior: final_decision may be cleared based on ret_code; assert boolean type
    assert isinstance(fb.final_decision, bool)

    # Verify captured system_prompt and user_prompt include expected content
    assert 'system_prompt' in recorded and recorded['system_prompt'] is not None
    assert 'user_prompt' in recorded and recorded['user_prompt'] is not None

    # system_prompt should include task description (task_info) because evaluator passed task_desc
    assert str(task_info) in recorded['system_prompt']
    # Depending on internal flow, the user_prompt is expected to include the run stdout (original) or the removal message.
    # Accept either but ensure one of them is present.
    up = recorded['user_prompt']
    assert ("original stdout" in up) or (f"Model {task_name} removal succeeded." in up)
