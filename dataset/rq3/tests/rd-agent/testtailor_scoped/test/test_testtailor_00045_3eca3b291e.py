import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.data_science.proposal.exp_gen.draft.draft')
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
        """Ensure DSDraftExpGen._init_task_gen calls template rendering and APIBackend and returns parsed JSON."""
        # locate DSDraftExpGen class in loaded modules
        cls = None
        sys = __import__("sys")
        for m in list(sys.modules.values()):
            if not m:
                continue
            if hasattr(m, "DSDraftExpGen"):
                cls = getattr(m, "DSDraftExpGen")
                break
        self.assertIsNotNone(cls, "DSDraftExpGen class not found in imported modules")

        mod = sys.modules[cls.__module__]

        # backup originals
        orig_T = getattr(mod, "T", None)
        orig_API = getattr(mod, "APIBackend", None)

        try:
            # create simple mocks
            class _MockTemplateObj:
                def __init__(self, key):
                    self.key = key

                def r(self, **kwargs):
                    # return a deterministic string based on key and provided keys
                    return f"MOCK_PROMPT:{self.key}:{','.join(sorted(map(str, kwargs.keys())))}"

            def _MockT(key):
                return _MockTemplateObj(key)

            class _MockAPIBackend:
                def build_messages_and_create_chat_completion(self, user_prompt, system_prompt, json_mode, json_target_type):
                    # ensure we get prompts as expected (strings)
                    assert isinstance(user_prompt, str)
                    assert isinstance(system_prompt, str)
                    # return JSON string
                    return '{"description": "generated description", "model_name": "generated_model"}'

            # patch module
            mod.T = _MockT
            mod.APIBackend = _MockAPIBackend

            # call the target method as an unbound function (pass None as self)
            result = cls._init_task_gen(
                None,
                targets="Model",
                scenario_desc="scenario-desc",
                task_output_format="some-format",
                workspace_code=None,
                spec="spec-content",
                hypothesis=None,
                exp_and_feedback_desc=None,
                former_task=None,
            )

            # assertions on returned dict
            self.assertIsInstance(result, dict)
            self.assertEqual(result.get("description"), "generated description")
            self.assertEqual(result.get("model_name"), "generated_model")
        finally:
            # restore originals
            if orig_T is not None:
                mod.T = orig_T
            else:
                if hasattr(mod, "T"):
                    delattr(mod, "T")
            if orig_API is not None:
                mod.APIBackend = orig_API
            else:
                if hasattr(mod, "APIBackend"):
                    delattr(mod, "APIBackend")
