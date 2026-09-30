import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.qlib.factor_experiment_loader.pdf_loader')
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
        """complete the test case here"""
        # locate the module that defines classify_report_from_dict
        sys = __import__("sys")
        target_func = None
        target_module = None
        for m in list(sys.modules.values()):
            if not m:
                continue
            if hasattr(m, "classify_report_from_dict"):
                target_module = m
                target_func = getattr(m, "classify_report_from_dict")
                break

        self.assertIsNotNone(target_func, "classify_report_from_dict not found in any loaded module")

        # Provide safe replacements for external dependencies used inside the function
        class DummyT:
            def __init__(self, arg):
                self.arg = arg

            def r(self):
                return "dummy system prompt"

        class DummyAPIBackend:
            def __init__(self):
                # chat_token_limit is read from an instance in the code
                self.chat_token_limit = 1000

            def build_messages_and_calculate_token(self, user_prompt=None, system_prompt=None):
                # small token count so trimming loop is skipped
                return 10

            def build_messages_and_create_chat_completion(self, user_prompt=None, system_prompt=None, json_mode=True):
                # return a JSON string that the function expects and can parse
                return '{"class": 1}'

        # Ensure tqdm exists in the module (some modules may not have imported it)
        if not hasattr(target_module, "tqdm"):
            setattr(target_module, "tqdm", lambda x: x)

        # Patch the module-level names used by the function
        setattr(target_module, "T", DummyT)
        setattr(target_module, "APIBackend", DummyAPIBackend)

        # Prepare input: key must end with .pdf and value must be a string
        input_dict = {"report.pdf": "This is the content of the report."}

        # Call the function under test
        result = target_func(input_dict, vote_time=1)

        # Validate the output structure and classification result
        self.assertIsInstance(result, dict)
        self.assertIn("report.pdf", result)
        self.assertIsInstance(result["report.pdf"], dict)
        self.assertIn("class", result["report.pdf"])
        self.assertEqual(result["report.pdf"]["class"], 1)
