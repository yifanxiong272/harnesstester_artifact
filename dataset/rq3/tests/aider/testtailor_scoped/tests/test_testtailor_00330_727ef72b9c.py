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
        """Trigger the loop where total > model_max_input_tokens on the first iteration."""
        # token counting helper (same semantics as reference tests)
        def count(msg):
            if isinstance(msg, list):
                return sum(count(m) for m in msg)
            return len(msg["content"].split())

        # prepare a mock model with a very small max_input_tokens so the adjusted
        # model_max_input_tokens becomes negative (forcing the break on first loop iter)
        mock_model = unittest.mock.Mock()
        mock_model.name = "gpt-test"
        mock_model.token_count = count
        mock_model.info = {"max_input_tokens": 1}  # will become 1 - 512 = negative
        mock_model.simple_send_with_retries = unittest.mock.Mock(return_value="unused")

        # ChatSummary with max_tokens small but less than the total tokens of messages
        chat_summary = ChatSummary(mock_model, max_tokens=10)

        # Build messages: length > min_split (min_split == 4).
        # Last message is long to ensure split_index stays at len(messages)
        messages = [
            {"role": "user", "content": "one"},
            {"role": "assistant", "content": "two"},
            {"role": "user", "content": "three"},
            {"role": "assistant", "content": "four"},
            {"role": "user", "content": "five"},
            {"role": "assistant", "content": " ".join(["word"] * 20)},
        ]

        # Patch summarize_all to return a deterministic summary and observe its call args.
        with unittest.mock.patch.object(
            chat_summary, "summarize_all", return_value=[{"role": "user", "content": "Summary"}]
        ) as mock_summarize_all:
            result = chat_summary.summarize(messages)

            # Because model_max_input_tokens is negative, the loop in summarize_real
            # will break on the first iteration before appending any messages to 'keep',
            # so summarize_all should be called with an empty list.
            mock_summarize_all.assert_called_once_with([])

            # validate returned structure: summary returned and assistant appended by summarize()
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)
            self.assertEqual(result[0]["content"], "Summary")
            self.assertEqual(result[-1]["role"], "assistant")
