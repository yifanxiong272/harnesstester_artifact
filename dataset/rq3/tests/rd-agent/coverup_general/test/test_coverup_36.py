# file: rdagent/components/coder/data_science/ensemble/eval.py:25-100
# asked: {"lines": [34, 35, 38, 39, 41, 42, 43, 44, 45, 46, 47, 50, 51, 52, 55, 56, 57, 58, 59, 60, 61, 62, 64, 68, 69, 70, 71, 73, 75, 76, 77, 79, 81, 82, 83, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 99, 100], "branches": [[37, 41], [37, 42], [42, 43], [42, 50], [75, 76], [75, 79]]}
# gained: {"lines": [34, 35, 38, 39, 41, 42, 43, 44, 45, 46, 47, 50, 51, 52, 55, 56, 57, 58, 59, 60, 61, 62, 64, 68, 69, 70, 71, 73, 75, 76, 77, 79, 81, 82, 83, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 99, 100], "branches": [[37, 41], [37, 42], [42, 43], [42, 50], [75, 76], [75, 79]]}

import importlib
from types import SimpleNamespace
import pathlib

import pytest


# Import the module under test
eval_mod = importlib.import_module("rdagent.components.coder.data_science.ensemble.eval")
EnsembleCoSTEEREvaluator = eval_mod.EnsembleCoSTEEREvaluator
EnsembleEvalFeedback = eval_mod.EnsembleEvalFeedback


class FakeResult:
    def __init__(self, exit_code: int, stdout: str):
        self.exit_code = exit_code
        self._stdout = stdout

    def get_truncated_stdout(self):
        return self._stdout


class FakeImplementation:
    def __init__(self, file_dict=None, all_codes=""):
        self.file_dict = dict(file_dict or {})
        self.all_codes = all_codes
        self.injected = {}

    def inject_files(self, **kwargs):
        # emulate adding files into file_dict
        self.injected.update(kwargs)
        self.file_dict.update(kwargs)

    def run(self, env=None, entry=None):
        return getattr(self, "_run_result")

    def execute(self, env=None, entry=None):
        return getattr(self, "_execute_result")


class FakeTask:
    def __init__(self, info):
        self._info = info

    def get_task_information(self):
        return self._info


class DummyQueriedKnowledge:
    def __init__(self, success_map=None, failed_set=None):
        self.success_task_to_knowledge_dict = dict(success_map or {})
        self.failed_task_info_set = set(failed_set or ())


def make_evaluator_with_scen(metric_name="acc"):
    scen = SimpleNamespace(metric_name=metric_name, debug_path="/dbg", real_debug_timeout=lambda: 10)
    return EnsembleCoSTEEREvaluator(scen)


def test_evaluate_returns_feedback_from_queried_knowledge():
    evaluator = make_evaluator_with_scen()
    task = FakeTask("T1")
    # prepare a fake feedback object
    fake_feedback = EnsembleEvalFeedback(
        execution="exec",
        code="code",
        return_checking="ret",
        final_decision=True,
    )
    qk = DummyQueriedKnowledge(success_map={"T1": SimpleNamespace(feedback=fake_feedback)})

    result = evaluator.evaluate(target_task=task, implementation=None, gt_implementation=None, queried_knowledge=qk)
    assert result is fake_feedback


def test_evaluate_returns_skip_feedback_for_failed_task():
    evaluator = make_evaluator_with_scen()
    task = FakeTask("T-Failed")
    qk = DummyQueriedKnowledge(failed_set={"T-Failed"})

    result = evaluator.evaluate(target_task=task, implementation=None, gt_implementation=None, queried_knowledge=qk)
    # Check the textual fields and final_decision False as constructed in code paths
    assert isinstance(result, EnsembleEvalFeedback)
    assert result.execution == "This task has failed too many times, skip implementation."
    assert result.code == "This task has failed too many times, skip implementation."
    assert result.return_checking == "This task has failed too many times, skip implementation."
    assert result.final_decision is False


def test_full_evaluate_with_main_and_zero_exit(monkeypatch, tmp_path):
    # Prepare environment: create template file under eval_tests
    eval_tests_dir = tmp_path / "eval_tests"
    eval_tests_dir.mkdir()
    tpl_path = eval_tests_dir / "ensemble_test.txt"
    # Template uses model_names and metric_name
    tpl_path.write_text("Models: {{ model_names }} Metric: {{ metric_name }}")

    # Patch module DIRNAME to tmp_path
    monkeypatch.setattr(eval_mod, "DIRNAME", tmp_path)

    # Patch get_ds_env to return a dummy env object
    fake_env = object()
    monkeypatch.setattr(eval_mod, "get_ds_env", lambda extra_volumes, running_timeout_period: fake_env)

    # Patch T to return object with r method
    class FakeTObj:
        def __init__(self, text):
            self.text = text

        def r(self, **kwargs):
            # return a simple concatenation so we can inspect usage
            if "test_code" in kwargs:
                return f"SYSTEM({self.text}):{kwargs.get('task_desc')}|{kwargs.get('metric_name')}"
            return f"USER({self.text}):{kwargs.get('stdout')}|{kwargs.get('workflow_stdout')}"

    monkeypatch.setattr(eval_mod, "T", lambda txt: FakeTObj(txt))

    # Patch remove_eda_part to strip a marker
    monkeypatch.setattr(eval_mod, "remove_eda_part", lambda s: s.replace("[EDA]", ""))

    # Prepare FakeImplementation with model files and main.py
    impl = FakeImplementation(
        file_dict={"model_a.py": "m", "ensemble.py": "ens_code", "main.py": "print('hi')"},
        all_codes="allcodes",
    )
    # set run to return exit_code 0 and some stdout
    impl._run_result = FakeResult(0, "OK STDOUT")
    # set execute to return some workflow stdout containing EDA marker
    impl._execute_result = "WORKFLOW[EDA]"
    target_task = FakeTask("TTASK")

    # Capture arguments passed to build_cls_from_json_with_retry
    captured = {}

    def fake_build(cls, system_prompt=None, user_prompt=None, init_kwargs_update_func=None):
        captured["cls"] = cls
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        captured["init_kwargs_update_func"] = init_kwargs_update_func
        # return an object that resembles EnsembleEvalFeedback with final_decision True
        return SimpleNamespace(final_decision=True)

    monkeypatch.setattr(eval_mod, "build_cls_from_json_with_retry", fake_build)

    evaluator = make_evaluator_with_scen()
    result = evaluator.evaluate(target_task=target_task, implementation=impl, gt_implementation=None, queried_knowledge=None)
    # After successful run and main.py present and run exit code 0, final_decision remains True
    assert result.final_decision is True
    # Ensure build_cls_from_json_with_retry was called with EnsembleEvalFeedback as first arg
    assert captured["cls"] is EnsembleEvalFeedback
    # Ensure that the injected test file exists in implementation file_dict
    assert "test/ensemble_test.txt" in impl.file_dict
    # Ensure the system prompt contains our task description fragment
    assert "TTASK" in captured["system_prompt"]


def test_full_evaluate_no_main_or_nonzero_retcode(monkeypatch, tmp_path):
    # Prepare environment: create template file under eval_tests
    eval_tests_dir = tmp_path / "eval_tests"
    eval_tests_dir.mkdir()
    tpl_path = eval_tests_dir / "ensemble_test.txt"
    tpl_path.write_text("Models: {{ model_names }} Metric: {{ metric_name }}")

    monkeypatch.setattr(eval_mod, "DIRNAME", tmp_path)
    monkeypatch.setattr(eval_mod, "get_ds_env", lambda extra_volumes, running_timeout_period: object())

    class FakeTObj:
        def __init__(self, text):
            self.text = text

        def r(self, **kwargs):
            if "test_code" in kwargs:
                return "SYS_PROMPT"
            return "USER_PROMPT"

    monkeypatch.setattr(eval_mod, "T", lambda txt: FakeTObj(txt))
    monkeypatch.setattr(eval_mod, "remove_eda_part", lambda s: s)

    # Implementation without main.py and with non-zero exit code
    impl = FakeImplementation(file_dict={"model_b.py": "m", "ensemble.py": "ens"}, all_codes="allcodes")
    impl._run_result = FakeResult(1, "BAD OUTPUT")  # non-zero exit code
    target_task = FakeTask("TT2")

    def fake_build(cls, system_prompt=None, user_prompt=None, init_kwargs_update_func=None):
        # return object with final_decision True initially
        return SimpleNamespace(final_decision=True)

    monkeypatch.setattr(eval_mod, "build_cls_from_json_with_retry", fake_build)

    evaluator = make_evaluator_with_scen()
    result = evaluator.evaluate(target_task=target_task, implementation=impl, gt_implementation=None, queried_knowledge=None)
    # Because run returned non-zero exit code, final_decision should be False
    assert result.final_decision is False
    # Ensure the injected test file exists
    assert "test/ensemble_test.txt" in impl.file_dict
