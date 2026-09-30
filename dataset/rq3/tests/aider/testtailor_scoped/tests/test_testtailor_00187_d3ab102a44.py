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
        """Trigger ValueError when no models are available for summarization."""
        mock_model = unittest.mock.Mock()
        mock_model.name = "gpt-3.5-turbo"
        mock_model.token_count = lambda msg: len(msg["content"].split())
        mock_model.info = {"max_input_tokens": 4096}
        mock_model.simple_send_with_retries = unittest.mock.Mock(return_value="irrelevant")

        chat_summary = ChatSummary(mock_model, max_tokens=100)

        # Simulate models being removed after initialization
        chat_summary.models = []

        messages = [{"role": "user", "content": "Hello world"}]

        with self.assertRaisesRegex(ValueError, "No models available for summarization"):
            chat_summary.summarize_real(messages)
