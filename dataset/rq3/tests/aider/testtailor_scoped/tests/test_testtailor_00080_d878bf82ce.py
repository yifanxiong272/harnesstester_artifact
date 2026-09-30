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
        """Test format_messages handles list content with dict item whose value is not a URL dict."""
        messages = [
            {
                "role": "assistant",
                "content": [
                    {"caption": "An image of a cat"},
                ],
            }
        ]

        # Call the function under test
        output = format_messages(messages, title="Gallery")

        # Title should be uppercased and followed by stars
        self.assertIn("GALLERY " + "*" * 50, output)
        # Separator added for each message
        self.assertIn("-------", output)
        # Target line: role uppercased, key as-is, and value rendered
        self.assertIn("ASSISTANT caption: An image of a cat", output)
