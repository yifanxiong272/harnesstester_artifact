import importlib
import re
from types import SimpleNamespace
import pytest


MODULE_PATH = "rdagent.components.coder.data_science.raw_data_loader.eval"


def make_fake_target(task_info):
    return SimpleNamespace(get_task_information=lambda: task_info)


def test_success_queried_feedback_round_096():
    eval_mod = importlib.import_module(MODULE_PATH)

    # Prepare a fake self (no real CoSTEER parent initialization required)
    fake_self = SimpleNamespace(scen=SimpleNamespace(debug_path="dbg", real_debug_timeout=lambda: 123))

    # target task that maps to a success entry
    target = make_fake_target("task_ok")

    # queried_knowledge with a success mapping that contains a 'feedback' attribute
    sentinel_feedback = object()
    queried_knowledge = SimpleNamespace(
        success_task_to_knowledge_dict={"task_ok": SimpleNamespace(feedback=sentinel_feedback)},
        failed_task_info_set=set(),
    )

    # Call the evaluate function directly; this should short-circuit and return the feedback object
    result = eval_mod.DataLoaderCoSTEEREvaluator.evaluate(fake_self, target, None, None, queried_knowledge=queried_knowledge)

    assert result is sentinel_feedback


def test_failed_queried_feedback_round_096():
    eval_mod = importlib.import_module(MODULE_PATH)

    # Patch the DataLoaderEvalFeedback symbol in the module to a simple class we control
    class DummyFeedback:
        def __init__(self, **kwargs):
            # mirror construction in source: execution, return_checking, code, final_decision
            for k, v in kwargs.items():
                setattr(self, k, v)

        @staticmethod
        def val_and_update_init_dict(d):
            # Minimal contract: accept and return a dict-like init kwargs update function
            return d

    eval_mod.DataLoaderEvalFeedback = DummyFeedback

    fake_self = SimpleNamespace(scen=SimpleNamespace(debug_path="dbg", real_debug_timeout=lambda: 123))
    target = make_fake_target("task_fail")

    queried_knowledge = SimpleNamespace(
        success_task_to_knowledge_dict={},
        failed_task_info_set={"task_fail"},
    )

    # Expect a DummyFeedback instance with specific messages and final_decision False
    fb = eval_mod.DataLoaderCoSTEEREvaluator.evaluate(fake_self, target, None, None, queried_knowledge=queried_knowledge)

    assert isinstance(fb, DummyFeedback)
    assert fb.execution == "This task has failed too many times, skip implementation."
    assert fb.return_checking == "This task has failed too many times, skip implementation."
    assert fb.code == "This task has failed too many times, skip implementation."
    assert fb.final_decision is False


def test_full_flow_truncation_and_workflow_execute_round_096(monkeypatch):
    eval_mod = importlib.import_module(MODULE_PATH)

    # Fake self with scen attributes used to build extra_volumes and timeout
    fake_self = SimpleNamespace(scen=SimpleNamespace(debug_path="dbg_path", real_debug_timeout=lambda: 999))
    target = make_fake_target("some_task")

    # Patch T to return objects with r(...) that produce predictable prompts
    class DummyT:
        def __init__(self, key):
            self.key = key

        def r(self, **kwargs):
            # return a string that includes key and some of kwargs for easier assertions
            # we purposely include eda_output if present so we can observe truncation message
            return f"TEMPLATE[{self.key}]|{kwargs}"

    monkeypatch.setattr(eval_mod, "T", DummyT)

    # Patch get_ds_env to return a dummy environment object and capture extra_volumes
    captured = {}

    def fake_get_ds_env(extra_volumes=None, running_timeout_period=None):
        captured['extra_volumes'] = extra_volumes
        captured['timeout'] = running_timeout_period
        return "FAKE_ENV"

    monkeypatch.setattr(eval_mod, "get_ds_env", fake_get_ds_env)

    # Create a fake implementation (mimicking FBWorkspace) required methods/attributes
    class FakeResult:
        def __init__(self, stdout, exit_code):
            self._stdout = stdout
            self.exit_code = exit_code

        def get_truncated_stdout(self):
            return self._stdout

    class FakeImplementation:
        def __init__(self):
            # include main.py and load_data.py as expected by the code
            self.file_dict = {
                "main.py": "print('main')",
                "load_data.py": "def load(): pass",
            }
            self.all_codes = "# all codes"
            self.injected = {}
            self.executed = False

        def inject_files(self, **kwargs):
            self.injected.update(kwargs)
            # mimic storing the test file in file_dict so code can possibly use it
            self.file_dict.update(kwargs)

        def run(self, env=None, entry=None):
            # Build a stdout that contains a huge EDA part between markers
            prefix = "PRE-STDOUT"
            # create EDA content with >10000 words
            eda_words = ("x " * 10050).strip()
            eda_section = f"=== Start of EDA part ==={eda_words}=== End of EDA part ==="
            suffix = "POST-STDOUT"
            full = prefix + eda_section + suffix
            return FakeResult(full, 0)

        def execute(self, env=None, entry=None):
            self.executed = True
            # Return some workflow stdout (which will be stripped by remove_eda_part)
            return "workflow output with maybe EDA markers"

    impl = FakeImplementation()

    # Patch remove_eda_part to a predictable function
    monkeypatch.setattr(eval_mod, "remove_eda_part", lambda s: "WORKFLOW_STRIPPED")

    # Capture the user_prompt passed to build_cls_from_json_with_retry
    captured_user_prompts = []

    def fake_build_cls_from_json_with_retry(cls, system_prompt=None, user_prompt=None, init_kwargs_update_func=None):
        captured_user_prompts.append(user_prompt)
        # Return an object with final_decision attribute which is later modified by the code under test
        return SimpleNamespace(final_decision=True)

    monkeypatch.setattr(eval_mod, "build_cls_from_json_with_retry", fake_build_cls_from_json_with_retry)

    # Ensure DataLoaderEvalFeedback on module has the expected val_and_update_init_dict attribute
    # If prior tests replaced it, provide a minimal implementation here as well.
    if not hasattr(eval_mod.DataLoaderEvalFeedback, "val_and_update_init_dict"):
        def _minimal_val_and_update_init_dict(d):
            return d

        try:
            setattr(eval_mod.DataLoaderEvalFeedback, "val_and_update_init_dict", staticmethod(_minimal_val_and_update_init_dict))
        except Exception:
            # Fallback: replace the symbol with a minimal class providing the attribute
            class MinimalFB:
                @staticmethod
                def val_and_update_init_dict(d):
                    return d

            eval_mod.DataLoaderEvalFeedback = MinimalFB

    # Now call evaluate with no queried_knowledge so the normal flow runs
    fb = eval_mod.DataLoaderCoSTEEREvaluator.evaluate(fake_self, target, impl, None, queried_knowledge=None)

    # fb should be the object returned by our fake builder and final_decision should remain True
    assert hasattr(fb, "final_decision")
    assert fb.final_decision is True

    # Ensure the implementation.execute path was taken (execute called) because main.py exists and ret_code == 0
    assert impl.executed is True

    # The captured user_prompt should include the truncated-EDA message appended by the code
    # Our DummyT.r returns a stringified kwargs; the eda_output (after truncation) is passed inside user_prompt
    assert len(captured_user_prompts) == 1
    user_prompt = captured_user_prompts[0]
    assert user_prompt is not None
    # The truncation message should be present when EDA content had >10000 words
    assert "Length of EDA output is too long, truncated. Please reject this implementation and motivate it to reduce the length of EDA output." in user_prompt
