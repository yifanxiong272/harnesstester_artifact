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
        """Test format_messages handles list content with dict containing a URL value."""
        # Prepare a message where content is a list containing a dict whose value
        # is a dict that includes a 'url' key. This should trigger the target branch.
        messages = [
            {
                "role": "assistant",
                "content": [
                    {"photo": {"url": "https://example.com/pic.png"}},
                ],
            }
        ]

        # Call the function under test with a title to also exercise the title branch.
        output = format_messages(messages, title="media")

        # The role is uppercased and the key is capitalized, with " URL: " before the url.
        expected_line = "ASSISTANT Photo URL: https://example.com/pic.png"
        self.assertIn(expected_line, output)

        # Also verify the title line was added and separators are present.
        self.assertTrue(output.startswith("MEDIA " + "*" * 50))
        self.assertIn("-------", output)
