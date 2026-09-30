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
    def test_get_rerun_summary_message_with_screenshot(self):
        """get_rerun_summary_message should produce a multi-part UserMessage when a screenshot is provided."""
        prompt = "Please summarize the rerun results."
        screenshot_b64 = "dGVzdF9iYXNlNjRfc3RyaW5n"  # arbitrary base64-like string

        msg = get_rerun_summary_message(prompt=prompt, screenshot_b64=screenshot_b64)

        # Top-level message shape
        self.assertIsInstance(msg, UserMessage)
        self.assertIsInstance(msg.content, list)

        # Expect exactly two parts: text then image
        self.assertEqual(len(msg.content), 2)

        text_part, image_part = msg.content[0], msg.content[1]

        # Validate text part
        self.assertIsInstance(text_part, ContentPartTextParam)
        self.assertEqual(text_part.type, 'text')
        self.assertEqual(text_part.text, prompt)

        # Validate image part
        self.assertIsInstance(image_part, ContentPartImageParam)
        self.assertEqual(image_part.type, 'image_url')
        self.assertIsInstance(image_part.image_url, ImageURL)
        expected_url = f'data:image/png;base64,{screenshot_b64}'
        self.assertEqual(image_part.image_url.url, expected_url)

        # UserMessage.text should extract the text portion correctly
        self.assertEqual(msg.text, prompt)
