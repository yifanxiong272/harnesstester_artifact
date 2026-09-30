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
        """Ensure the head is trimmed back to the last assistant message before summarizing."""
        # token counting helper that handles both single messages and lists (as used by ChatSummary)
        def count(msg):
            if isinstance(msg, list):
                return sum(count(m) for m in msg)
            return len(msg["content"].split())

        mock_model = unittest.mock.Mock()
        mock_model.name = "test-model"
        mock_model.token_count = count
        mock_model.info = {"max_input_tokens": 4096}
        mock_model.simple_send_with_retries = unittest.mock.Mock(return_value="AUTO_SUMMARY")

        # Small max_tokens so summarization logic runs and the reverse-tail scan picks a split index
        chat_summary = ChatSummary(mock_model, max_tokens=20)

        # Build messages so that the initial split_index points to a location
        # where the previous message is a user; the loop should decrement to the
        # earlier assistant message.
        roles = ["assistant", "user", "user", "user", "assistant", "user", "user", "user"]
        messages = []
        for r in roles:
            # 5 tokens per message to make token math predictable
            messages.append({"role": r, "content": " ".join(["tok"] * 5)})

        # Patch summarize_all to assert that the head passed to it ends with an assistant message.
        def fake_summarize_all(input_messages):
            # The target code should have adjusted split_index so that the head ends with an assistant
            self.assertTrue(len(input_messages) > 0)
            self.assertEqual(input_messages[-1]["role"], "assistant")
            # Return a simple summary message (the real summarize_all returns a list)
            return [{"role": "user", "content": "Summary"}]

        with unittest.mock.patch.object(chat_summary, "summarize_all", side_effect=fake_summarize_all) as patched:
            result = chat_summary.summarize(messages)

        # summarize_all should have been invoked (verifying our assertion ran)
        patched.assert_called_once()

        # Result should be a list and end with an assistant reply (ChatSummary.summarize appends "Ok." if needed)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        self.assertEqual(result[-1]["role"], "assistant")
