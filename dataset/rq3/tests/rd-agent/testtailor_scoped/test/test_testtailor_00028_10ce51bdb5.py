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
        # prepare a minimal report dict with a .pdf key and string content
        report_dict = {"sample_report.pdf": "This is a short test content."}

        # locate the module where the target function is defined
        mod_name = classify_report_from_dict.__module__

        # create fakes for T and APIBackend to avoid external dependencies / network calls
        class _FakeT:
            def __init__(self, arg):
                self.arg = arg

            def r(self):
                return "fake_system_prompt"

        class FakeAPIBackend:
            # make chat_token_limit reasonably large so truncation loop is skipped
            chat_token_limit = 1000

            def build_messages_and_calculate_token(self, user_prompt, system_prompt):
                # return a small token count
                return 10

            def build_messages_and_create_chat_completion(self, user_prompt, system_prompt, json_mode=True):
                # return a JSON string that the function will parse
                return '{"class": "1"}'

        # patch T and APIBackend in the module of the target function
        with unittest.mock.patch(f"{mod_name}.T", new=_FakeT), unittest.mock.patch(
            f"{mod_name}.APIBackend", new=FakeAPIBackend
        ):
            result = classify_report_from_dict(report_dict, vote_time=1)

        # verify the output structure and classification value
        self.assertIsInstance(result, dict)
        self.assertIn("sample_report.pdf", result)
        self.assertEqual(result["sample_report.pdf"], {"class": 1})
