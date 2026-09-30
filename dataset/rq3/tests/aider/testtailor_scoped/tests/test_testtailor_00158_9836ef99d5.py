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
        """summarize should append an assistant 'Ok.' message when the last message is not from assistant"""
        # Create a minimal mock model required by ChatSummary without relying on an external 'mock' name
        mock_model = unittest.mock.Mock()
        mock_model.name = "gpt-3.5-turbo"
        mock_model.token_count = lambda msg: len(msg["content"].split()) if isinstance(msg, dict) else 0
        mock_model.info = {"max_input_tokens": 4096}
        mock_model.simple_send_with_retries = unittest.mock.Mock()

        chat_summary = ChatSummary(mock_model, max_tokens=100)

        # Replace summarize_real on the instance to return a list whose last message is from 'user'
        def fake_summarize_real(messages, depth=0):
            return [{"role": "user", "content": "Needs summary"}]

        chat_summary.summarize_real = fake_summarize_real

        result = chat_summary.summarize([{"role": "user", "content": "ignored input"}])

        # Verify that the assistant "Ok." message was appended
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 2)
        self.assertEqual(result[-1], {"role": "assistant", "content": "Ok."})
        # Ensure the original returned content is preserved before the appended message
        self.assertEqual(result[0]["role"], "user")
        self.assertEqual(result[0]["content"], "Needs summary")
