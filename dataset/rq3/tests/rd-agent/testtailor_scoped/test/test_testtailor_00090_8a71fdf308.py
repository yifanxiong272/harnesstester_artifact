import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.data_science.share.util')
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
        """Ensure blank line after the first print triggers the 'continue' branch and comments are collected."""
        code = "print('Section: Test')\n\n# First comment\n#Second comment\nx = 1\n"
        comments, cleaned = extract_comment_under_first_print(code)

        self.assertEqual(comments, "First comment\nSecond comment")
        self.assertEqual(cleaned, "print('Section: Test')\n\nx = 1")
