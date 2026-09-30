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
        """Ensure summarize() appends an assistant 'Ok.' when last role is not assistant."""
        # Create a minimal mock model acceptable to ChatSummary (no spec to avoid NameError)
        mock_model = unittest.mock.Mock()
        mock_model.name = "gpt-test"
        # Keep token_count small so summarize_real returns messages unchanged
        mock_model.token_count = lambda msg: 1
        mock_model.info = {"max_input_tokens": 4096}
        mock_model.simple_send_with_retries = unittest.mock.Mock(return_value="unused")

        chat_summary = ChatSummary(mock_model, max_tokens=100)

        # Prepare messages where the last message is NOT from assistant
        messages = [{"role": "user", "content": "Hello world"}]

        result = chat_summary.summarize(messages)

        # Expect an "Ok." assistant message appended
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["role"], "user")
        self.assertEqual(result[0]["content"], "Hello world")
        self.assertEqual(result[-1], {"role": "assistant", "content": "Ok."})
