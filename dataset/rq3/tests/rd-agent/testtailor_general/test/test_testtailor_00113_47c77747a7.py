import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.model_coder.task_loader')
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
        """Find a module that defines extract_model_from_doc, patch its dependencies and call it."""
        # locate a loaded rdagent module that defines the target function
        sys_mod = __import__("sys")
        target_module = None
        for name, module in list(sys_mod.modules.items()):
            if not isinstance(name, str):
                continue
            if not name.startswith("rdagent"):
                continue
            if module is None:
                continue
            if hasattr(module, "extract_model_from_doc") and callable(getattr(module, "extract_model_from_doc")):
                target_module = module
                break

        if target_module is None:
            self.skipTest("No rdagent module with extract_model_from_doc is loaded")

        # Create dummy implementations for APIBackend and T used inside the function
        class DummySession:
            def __init__(self):
                self.calls = []

            def build_chat_completion(self, user_prompt, json_mode=False):
                # record call for potential inspection and return a valid JSON wrapped in a ```json ... ``` block
                self.calls.append((user_prompt, json_mode))
                return '```json{\"M1\": {\"description\": \"d\", \"formulation\": \"f\", \"variables\": {}}}```'

        class DummyAPIBackend:
            def __init__(self):
                pass

            def build_chat_session(self, session_system_prompt=None):
                # return a DummySession instance (mimics the real session)
                return DummySession()

        def DummyT(s):
            class _T:
                def __init__(self, s):
                    self.s = s

                def r(self):
                    return f"translated:{self.s}"

            return _T(s)

        # Patch the module's names
        setattr(target_module, "APIBackend", DummyAPIBackend)
        setattr(target_module, "T", DummyT)

        # Call the function under test
        result = target_module.extract_model_from_doc("some document content")

        # Basic validations: should return a dict with parsed model information
        self.assertIsInstance(result, dict)
        self.assertIn("M1", result)
        self.assertIsInstance(result["M1"], dict)
        self.assertEqual(result["M1"].get("description"), "d")
