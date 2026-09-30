import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.tools.pr_help_docs')
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
        ai_response = (
            "### Question: \n"
            "How does one request to re-review a PR?\n\n"
            "### Answer:\n"
            "According to the documentation, one needs to invoke the command: /review\n\n"
            "#### Relevant Sources:\n\n"
            "- https://docs.example.com/review\n"
        )
        result = modify_answer_section(ai_response)
        expected_tail = ai_response.split("### Answer:\n")[-1]
        expected = "### :bulb: Auto-generated documentation-based answer:\n" + expected_tail
        self.assertEqual(result, expected)
