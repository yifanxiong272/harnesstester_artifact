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
        # Create a mock model using unittest.mock to avoid relying on 'mock' name
        mock_model = unittest.mock.Mock()
        mock_model.name = "gpt-test"
        # token_count counts words in the message content
        mock_model.token_count = lambda msg: len(msg["content"].split())
        mock_model.info = {"max_input_tokens": 4096}
        mock_model.simple_send_with_retries = unittest.mock.Mock()

        # Use a very small max_tokens so the total tokens exceed it and trigger the len(messages) check
        chat_summary = ChatSummary(mock_model, max_tokens=3)

        # Prepare exactly min_split (4) messages so len(messages) <= min_split triggers summarize_all
        messages = [
            {"role": "user", "content": "one two"},
            {"role": "assistant", "content": "one two"},
            {"role": "user", "content": "one two"},
            {"role": "assistant", "content": "one two"},
        ]

        # Replace summarize_all with a mock and assert that summarize_real returns its value
        sentinel = [{"role": "user", "content": "SENTINEL"}]
        chat_summary.summarize_all = unittest.mock.Mock(return_value=sentinel)

        result = chat_summary.summarize_real(messages)

        chat_summary.summarize_all.assert_called_once_with(messages)
        self.assertEqual(result, sentinel)
