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
        """Force summarize_real to take the recursion branch that returns
        self.summarize_real(summary + tail, depth + 1).
        """
        # Create a mock model via unittest.mock
        mock_model = unittest.mock.Mock()
        mock_model.name = "test-model"
        mock_model.info = {"max_input_tokens": 4096}

        # token_count that handles both dict messages and lists of messages
        def token_count(msg):
            if isinstance(msg, list):
                return sum(token_count(m) for m in msg)
            # Count tokens as number of words in content
            return len(msg["content"].split())

        mock_model.token_count = token_count
        # simple_send_with_retries won't be used because we'll patch summarize_all on the instance
        mock_model.simple_send_with_retries = unittest.mock.Mock(return_value="unused")

        # Create ChatSummary with a small max_tokens so summarization is triggered
        chat_summary = ChatSummary(mock_model, max_tokens=20)

        # Build messages: 10 messages alternating user/assistant, 3 tokens each -> total 30 > 20
        messages = []
        for i in range(10):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({"role": role, "content": "word word word"})

        # Prepare two summarize_all returns:
        # - First (long) summary to ensure summary_tokens + tail_tokens >= max_tokens -> triggers recursion
        # - Second (short) summary to allow recursive call to finish and return a result
        long_summary = [dict(role="user", content=" ".join(["sum"] * 12))]  # 12 tokens
        final_summary = [dict(role="user", content="final")]  # 1 token

        # Patch the instance method summarize_all to return the two prepared summaries in sequence
        chat_summary.summarize_all = unittest.mock.Mock(side_effect=[long_summary, final_summary])

        # Call summarize_real which should follow the path to the recursive return
        result = chat_summary.summarize_real(messages)

        # Ensure summarize_all was called at least twice (indicating recursion took place)
        self.assertGreaterEqual(chat_summary.summarize_all.call_count, 2)

        # Final result should be the final_summary (from the recursive call)
        self.assertIsInstance(result, list)
        self.assertEqual(result, final_summary)
