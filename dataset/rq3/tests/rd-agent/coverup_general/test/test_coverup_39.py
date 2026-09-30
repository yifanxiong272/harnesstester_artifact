# file: rdagent/components/coder/data_science/raw_data_loader/eval.py:27-94
# asked: {"lines": [35, 37, 38, 40, 41, 42, 43, 44, 45, 46, 49, 50, 51, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 67, 68, 69, 71, 73, 74, 75, 76, 77, 78, 80, 81, 82, 83, 86, 88, 89, 92, 94], "branches": [[36, 40], [36, 41], [41, 42], [41, 49], [64, 65], [64, 67], [67, 68], [67, 71]]}
# gained: {"lines": [35, 37, 38, 40, 41, 42, 43, 44, 45, 46, 49, 50, 51, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 67, 68, 69, 73, 74, 75, 76, 77, 78, 80, 81, 82, 83, 86, 88, 89, 92, 94], "branches": [[36, 40], [36, 41], [41, 42], [41, 49], [64, 65], [67, 68]]}

import types
import re
from pathlib import Path

import pytest


MODULE_PATH = "rdagent.components.coder.data_science.raw_data_loader.eval"


def get_mod():
    import importlib

    return importlib.import_module(MODULE_PATH)


class DummyTask:
    def __init__(self, info):
        self._info = info

    def get_task_information(self):
        return self._info


class DummyQueriedSuccess:
    def __init__(self, mapping):
        self.success_task_to_knowledge_dict = mapping
        self.failed_task_info_set = set()


class DummyQueriedFailed:
    def __init__(self, failed_set):
        self.success_task_to_knowledge_dict = {}
        self.failed_task_info_set = set(failed_set)


def test_evaluate_returns_feedback_from_success_mapping():
    eval_mod = get_mod()
    # Access unbound function
    evaluate_fn = getattr(eval_mod.DataLoaderCoSTEEREvaluator, "evaluate")

    sentinel_feedback = object()
    task_info = "my_task"

    # queried_knowledge containing success mapping
    q = DummyQueriedSuccess({task_info: types.SimpleNamespace(feedback=sentinel_feedback)})

    # dummy self - no attributes needed for early return
    dummy_self = object()

    res = evaluate_fn(dummy_self, DummyTask(task_info), implementation=None, gt_implementation=None, queried_knowledge=q)
    assert res is sentinel_feedback


def test_evaluate_handles_failed_task_short_circuit():
    eval_mod = get_mod()
    evaluate_fn = getattr(eval_mod.DataLoaderCoSTEEREvaluator, "evaluate")

    task_info = "task_failed"
    q = DummyQueriedFailed({task_info})

    dummy_self = object()

    res = evaluate_fn(dummy_self, DummyTask(task_info), implementation=None, gt_implementation=None, queried_knowledge=q)
    # The function returns an object with expected attributes set in the code path
    # Check important attributes and values
    assert hasattr(res, "execution")
    assert "failed too many times" in res.execution
    assert hasattr(res, "final_decision")
    assert res.final_decision is False


def test_evaluate_full_flow(monkeypatch, tmp_path):
    eval_mod = get_mod()
    evaluate_fn = getattr(eval_mod.DataLoaderCoSTEEREvaluator, "evaluate")

    # Prepare a temporary eval_tests/data_loader_test.txt file for DIRNAME usage
    eval_tests_dir = tmp_path / "eval_tests"
    eval_tests_dir.mkdir()
    test_file = eval_tests_dir / "data_loader_test.txt"
    test_file.write_text("print('hello from data_loader_test')")
    # Patch DIRNAME in module so the read_text call finds our file
    monkeypatch.setattr(eval_mod, "DIRNAME", tmp_path)

    # Prepare a dummy T factory that returns an object with r()
    class DummyTObj:
        def __init__(self, key):
            self.key = key

        def r(self, *args, **kwargs):
            # Return a simple string for prompts or for volume paths
            return f"rendered:{self.key}:{kwargs}"

    def dummy_T(key):
        return DummyTObj(key)

    monkeypatch.setattr(eval_mod, "T", dummy_T)

    # Patch get_ds_env to a stub that just returns a marker object and records args
    captured = {}

    def fake_get_ds_env(extra_volumes=None, running_timeout_period=None):
        captured["extra_volumes"] = extra_volumes
        captured["running_timeout_period"] = running_timeout_period
        return {"env": "fake-env"}

    monkeypatch.setattr(eval_mod, "get_ds_env", fake_get_ds_env)

    # Patch remove_eda_part to identity
    monkeypatch.setattr(eval_mod, "remove_eda_part", lambda s: s)

    # Prepare a fake implementation (FBWorkspace-like)
    class FakeResult:
        def __init__(self, stdout, exit_code):
            self._stdout = stdout
            self.exit_code = exit_code

        def get_truncated_stdout(self):
            return self._stdout

    class FakeImplementation:
        def __init__(self):
            # initial file_dict must include load_data.py as accessed later
            self.file_dict = {"load_data.py": "print('load')", "main.py": "print('main')"}
            self.all_codes = "CODE: load_data.py and main.py"
            self.injected = {}

        def inject_files(self, **kwargs):
            # emulate injection by updating file_dict and recording call
            self.injected.update(kwargs)
            for k, v in kwargs.items():
                self.file_dict[k] = v

        def run(self, env, entry):
            assert env == {"env": "fake-env"}
            # create stdout with an EDA part that is long enough to trigger truncation branch
            eda_words = ["w"] * 10050  # > 10000 words to trigger branch at line ~64
            eda = " ".join(eda_words)
            stdout = "PRE_EDA\n=== Start of EDA part ===\n" + eda + "\n=== End of EDA part ===\nPOST_EDA\n"
            return FakeResult(stdout, 0)

        def execute(self, env, entry):
            # emulate running main.py and returning some workflow stdout
            return "workflow stdout with maybe EDA === Start of EDA part === hidden === End of EDA part === done"

    impl = FakeImplementation()

    # Patch build_cls_from_json_with_retry to return a simple feedback-like object
    build_called = {}

    class FakeFeedback:
        def __init__(self):
            self.final_decision = True
            self.execution = "exec"
            self.return_checking = "ret"
            self.code = "code"
            self.some_marker = "created"

    def fake_build(cls, system_prompt=None, user_prompt=None, init_kwargs_update_func=None):
        # validate that the stub receives expected parameters in call (basic check)
        build_called["cls"] = cls
        build_called["system_prompt"] = system_prompt
        build_called["user_prompt"] = user_prompt
        build_called["init_kwargs_update_func"] = init_kwargs_update_func
        return FakeFeedback()

    monkeypatch.setattr(eval_mod, "build_cls_from_json_with_retry", fake_build)

    # Construct a dummy self with scen attributes used in evaluate
    class DummyScen:
        def __init__(self):
            self.debug_path = "debug_path_value"

        def real_debug_timeout(self):
            return 999

    dummy_self = types.SimpleNamespace(scen=DummyScen())

    # Call evaluate
    fb = evaluate_fn(dummy_self, DummyTask("my_full_task"), implementation=impl, gt_implementation=None, queried_knowledge=None)

    # Verify that the injected test file is present in implementation.file_dict
    assert "test/data_loader_test.py" in impl.file_dict
    # verify that get_ds_env was called with the T-rendered extra volumes key
    assert "extra_volumes" in captured
    # debug_path key should be present in extra_volumes (even if value is dummy)
    assert dummy_self.scen.debug_path in captured["extra_volumes"]
    # Build function should have been called and returned our FakeFeedback
    assert isinstance(fb, FakeFeedback)
    # final_decision should remain True because exit_code == 0
    assert fb.final_decision is True
    # ensure build was called with a Feedback-like class and that init kwargs updater name is as expected
    assert build_called["cls"].__name__.endswith("Feedback")
    assert callable(build_called["init_kwargs_update_func"])
    assert "val_and_update_init_dict" in build_called["init_kwargs_update_func"].__name__
