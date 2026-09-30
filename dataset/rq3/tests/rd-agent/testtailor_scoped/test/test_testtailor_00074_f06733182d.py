import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.model_coder.evolving_strategy')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_XX(self):
        """Test that implement_one_task builds prompts and returns JSON-parsed code using stubbed globals."""
        # Prepare a minimal target task
        target_task = ModelTask(
            "test_model",
            "a test model",
            "test_arch",
            hyperparameters={},
            training_hyperparameters={},
        )
        model_information_str = target_task.get_task_information()

        # Prepare queried knowledge (V2 to trigger the branch that picks the first failed trace)
        queried_knowledge = CoSTEERQueriedKnowledgeV2(
            task_to_former_failed_traces={model_information_str: ["failed_trace_1", "failed_trace_2"]},
            task_to_similar_task_successful_knowledge={model_information_str: ["succ1", "succ2"]},
        )

        # Prepare a workspace with a model.py file injected
        workspace = FBWorkspace(target_task=target_task)
        workspace.inject_files(**{"model.py": "INITIAL_CODE"})

        # Build a dummy self with scen attribute expected by the method
        class DummyScen:
            def get_scenario_all_desc(self, filtered_tag="model"):
                return f"scenario_desc_for_{filtered_tag}"

        dummy_self = type("S", (), {"scen": DummyScen()})()

        # Obtain the function object and stash original globals to restore later
        func = ModelMultiProcessEvolvingStrategy.implement_one_task
        fn_globals = func.__globals__

        orig_T = fn_globals.get("T", None)
        orig_APIBackend = fn_globals.get("APIBackend", None)
        orig_CoSTEER_SETTINGS = fn_globals.get("CoSTEER_SETTINGS", None)

        # Stub Template factory T
        class DummyTemplate:
            def __init__(self, name):
                self.name = name

            def r(self, **kwargs):
                # Return different content for system vs user templates for clarity
                if "system" in self.name:
                    return "SYSTEM_PROMPT"
                return "USER_PROMPT"

        fn_globals["T"] = lambda name: DummyTemplate(name)

        # Stub APIBackend used in the method
        class StubAPIBackend:
            def __init__(self, use_chat_cache=None):
                self.chat_token_limit = 1000

            def build_messages_and_calculate_token(self, user_prompt, system_prompt):
                # Return a small token usage to allow loop to break immediately
                return 10

            def build_messages_and_create_chat_completion(self, user_prompt, system_prompt, json_mode, json_target_type):
                # Return a JSON string that contains a "code" field
                import json
                return json.dumps({"code": "def generated_model():\n    return 'ok'"})

        fn_globals["APIBackend"] = StubAPIBackend

        # Minimal CoSTEER_SETTINGS stub
        fn_globals["CoSTEER_SETTINGS"] = type("C", (), {"coder_use_cache": False})

        try:
            # Call the method (unbound) with our dummy self and prepared args
            returned_code = func(
                dummy_self,
                target_task=target_task,
                queried_knowledge=queried_knowledge,
                workspace=workspace,
                prev_task_feedback=None,
            )
        finally:
            # Restore globals to avoid side effects on other tests
            if orig_T is not None:
                fn_globals["T"] = orig_T
            else:
                fn_globals.pop("T", None)
            if orig_APIBackend is not None:
                fn_globals["APIBackend"] = orig_APIBackend
            else:
                fn_globals.pop("APIBackend", None)
            if orig_CoSTEER_SETTINGS is not None:
                fn_globals["CoSTEER_SETTINGS"] = orig_CoSTEER_SETTINGS
            else:
                fn_globals.pop("CoSTEER_SETTINGS", None)

        # Assert that the returned code matches what our StubAPIBackend produced
        self.assertIn("def generated_model()", returned_code)
        self.assertIn("return 'ok'", returned_code)
