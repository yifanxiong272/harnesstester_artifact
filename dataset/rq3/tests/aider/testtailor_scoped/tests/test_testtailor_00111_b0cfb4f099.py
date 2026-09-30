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
        """Ensure list-type message content with non-dict items is formatted with role prefix."""
        # Prepare a message where content is a list of non-dict items
        messages = [
            {"role": "user", "content": ["http://example.com/image.png", "a caption"]}
        ]

        # Call the function under test
        output = format_messages(messages)

        # The role should be uppercased and prefixed to each non-dict item in the list
        self.assertIn("USER http://example.com/image.png", output)
        self.assertIn("USER a caption", output)

        # There should be one separator line for the message
        self.assertIn("-------", output)

        # Ensure both list items produced exactly two occurrences of the role prefix
        self.assertEqual(output.count("USER "), 2)
