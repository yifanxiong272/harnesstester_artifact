import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.prompts')
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
        """get_rerun_summary_message returns a UserMessage with plain string content when no screenshot is provided."""
        prompt = "Please summarize the previous run and list key failures."
        msg = get_rerun_summary_message(prompt, screenshot_b64=None)

        # Returned object is a UserMessage
        self.assertIsInstance(msg, UserMessage)

        # When no screenshot is provided, content should be the original prompt string
        self.assertIsInstance(msg.content, str)
        self.assertEqual(msg.content, prompt)

        # The text property should parse and return the same prompt
        self.assertEqual(msg.text, prompt)

        # Ensure the string representation is reasonable (includes the class name)
        self.assertIn("UserMessage", str(msg))
