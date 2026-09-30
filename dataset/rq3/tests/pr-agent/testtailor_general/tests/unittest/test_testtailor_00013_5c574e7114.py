import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.tools.pr_help_message')
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
        # top-most header before the snippet content should be chosen
        snippet = "Header 1: Top Header\nSome other line\nHeader 2: Lower Header\n===Snippet content===\nbody"
        result = extract_header(snippet)
        self.assertEqual(result, "#top-header")

        # when there is no header before the snippet content, result should be empty
        snippet_no_header = "Just some text\nAnother line\n===Snippet content===\nbody"
        result_no_header = extract_header(snippet_no_header)
        self.assertEqual(result_no_header, "")
