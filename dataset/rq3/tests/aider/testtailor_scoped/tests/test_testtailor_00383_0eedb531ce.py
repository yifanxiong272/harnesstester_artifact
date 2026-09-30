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
        """Ensure messages with non-user/assistant roles are skipped when building the content
        sent to the summarizer (exercise the continue branch).
        """
        # create mock model using unittest.mock to avoid relying on a top-level 'mock' name
        mock_model = unittest.mock.Mock()
        mock_model.name = "test-model"

        # token counter that also handles being passed a list (used elsewhere in ChatSummary)
        def count(msg):
            if isinstance(msg, list):
                return sum(count(m) for m in msg)
            return len(msg["content"].split())

        mock_model.token_count = count
        mock_model.info = {"max_input_tokens": 4096}
        mock_model.simple_send_with_retries = unittest.mock.Mock(return_value="MODEL_SUMMARY")

        chat_summary = ChatSummary(mock_model, max_tokens=100)

        messages = [
            {"role": "system", "content": "Secret system note"},
            {"role": "user", "content": "Visible to summary"},
        ]

        result = chat_summary.summarize_all(messages)

        # ensure the model was invoked
        mock_model.simple_send_with_retries.assert_called_once()

        # inspect what was sent to the model: it's a list of two messages
        sent = mock_model.simple_send_with_retries.call_args[0][0]
        self.assertIsInstance(sent, list)
        self.assertEqual(len(sent), 2)

        # the second message passed to the model should contain only the user content,
        # and must NOT contain the system message text (the system message should have been skipped)
        self.assertIn("Visible to summary", sent[1]["content"])
        self.assertNotIn("Secret system note", sent[1]["content"])
        self.assertNotIn("# SYSTEM", sent[1]["content"])
        self.assertIn("# USER", sent[1]["content"])

        # check the returned summary contains the model's response
        self.assertEqual(result[0]["role"], "user")
        self.assertTrue(result[0]["content"].endswith("MODEL_SUMMARY"))
