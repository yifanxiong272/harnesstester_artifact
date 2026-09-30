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
        """Header selection picks the first header (earliest in file) before the marker."""
        snippet = (
            "Intro line\n"
            "Header 1: Top Header\n"
            "Some middle line\n"
            "Header 2: Bottom Header\n"
            "===Snippet content===\n"
            "snippet body here"
        )
        result = extract_header(snippet)
        # According to the implementation, the header chosen ends up being the first header in the file
        # (because the loop iterates reversed but later matches override earlier ones).
        self.assertEqual(result, "#top-header")

        # Also verify behavior when no headers are present before the marker
        snippet_no_header = "Just some text\nAnother line\n===Snippet content===\nrest"
        self.assertEqual(extract_header(snippet_no_header), "")
