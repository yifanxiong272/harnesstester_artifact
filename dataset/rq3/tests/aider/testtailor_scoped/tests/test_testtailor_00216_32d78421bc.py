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
        """Ensure summarize_real returns the original messages when total tokens <= max_tokens and depth == 0"""
        # Create a mock model using unittest.mock to avoid NameError for 'mock'
        mock_model = unittest.mock.Mock()
        mock_model.name = "gpt-test"
        # simple word count token function
        mock_model.token_count = lambda msg: len(msg["content"].split())
        mock_model.info = {"max_input_tokens": 4096}
        mock_model.simple_send_with_retries = unittest.mock.Mock()

        chat_summary = ChatSummary(mock_model, max_tokens=100)

        messages = [
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "Hi there"},
        ]

        # Call summarize_real directly to hit the early return when total <= max_tokens and depth == 0
        result = chat_summary.summarize_real(messages, depth=0)

        # Should return the exact same list object (early return)
        self.assertIs(result, messages)
        self.assertEqual(result, messages)
