import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.history')
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
        # Minimal fake model class to avoid relying on mock/imports
        class ModelMock:
            def __init__(self, name, response):
                self.name = name
                self._response = response
                self.info = {"max_input_tokens": 4096}
                self.call_count = 0

            def token_count(self, msg):
                # count tokens as words in the content
                return len(msg["content"].split())

            def simple_send_with_retries(self, messages):
                self.call_count += 1
                return self._response

        # Create the model and ChatSummary with a very small max_tokens
        model = ModelMock("gpt-3.5-turbo", "Summarized content")
        chat_summary = ChatSummary(model, max_tokens=5)

        # Four messages (== min_split). Each has two words -> total tokens = 8 > max_tokens.
        messages = [
            {"role": "user", "content": "one two"},
            {"role": "assistant", "content": "three four"},
            {"role": "user", "content": "five six"},
            {"role": "assistant", "content": "seven eight"},
        ]

        # This should hit the len(messages) <= min_split branch and call summarize_all
        result = chat_summary.summarize_real(messages)

        # validate results
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["role"], "user")
        # The model's returned text should appear at the end of the content (prefix may be added)
        self.assertTrue(result[0]["content"].endswith("Summarized content"))
        self.assertEqual(model.call_count, 1)
