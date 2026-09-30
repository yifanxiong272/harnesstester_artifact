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
        """summarize_real should raise when there are no models available for summarization"""
        # Create a mock model using unittest.mock to avoid relying on a top-level 'mock' import
        mock_model = unittest.mock.Mock()
        mock_model.name = "gpt-3.5-turbo"
        mock_model.token_count = lambda msg: len(msg["content"].split()) if isinstance(msg, dict) else 0
        mock_model.info = {"max_input_tokens": 4096}
        mock_model.simple_send_with_retries = unittest.mock.Mock(return_value="Summary")

        # Initialize ChatSummary with one model, then clear models to trigger the branch
        chat_summary = ChatSummary(mock_model, max_tokens=100)
        chat_summary.models = []

        messages = [{"role": "user", "content": "Hello world"}]

        with self.assertRaisesRegex(ValueError, "No models available for summarization"):
            chat_summary.summarize_real(messages)
