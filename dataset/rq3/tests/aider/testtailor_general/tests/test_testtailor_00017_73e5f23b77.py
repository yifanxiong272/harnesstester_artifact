import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.utils')
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
        """Ensure title header is rendered (uppercase + 50 asterisks) and message formatting works."""
        title = "my title"
        messages = [
            # multi-line content to exercise format_content
            {"role": "assistant", "content": "line1\nline2"},
            # list content with dict containing a nested url to exercise that branch
            {"role": "user", "content": [{"image": {"url": "http://img"}} , "caption"]},
            # simple single-line content plus a function_call to exercise that branch
            {"role": "system", "content": "single line", "function_call": "do_something"},
        ]

        out = format_messages(messages, title=title)

        # Header must contain the uppercase title and exactly 50 asterisks after a space
        expected_header = f"{title.upper()} {'*' * 50}"
        self.assertEqual(out.splitlines()[0], expected_header)

        # Check content formatting from format_content
        self.assertIn("ASSISTANT line1", out)
        self.assertIn("ASSISTANT line2", out)

        # Check list content handling with nested URL
        self.assertIn("USER Image URL: http://img", out)
        # Check non-dict item in list
        self.assertIn("USER caption", out)

        # Check function_call formatting
        self.assertIn("SYSTEM single line", out)
        self.assertIn("SYSTEM Function Call: do_something", out)
