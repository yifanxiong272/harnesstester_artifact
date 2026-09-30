import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.chat_chunks')
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
        """Ensure cacheable_messages reads all_messages and slices at a cache_control marker."""
        # Create a ChatChunks instance and populate its component lists
        chunks = ChatChunks()

        # A system message before the cacheable chunk
        chunks.system = [{"role": "system", "content": "system prompt"}]

        # A repo chunk that will be marked cacheable (content is a list with cache_control)
        chunks.repo = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "repo data", "cache_control": {"type": "ephemeral"}}
                ],
            }
        ]

        # Messages that come after the repo chunk
        chunks.done = [{"role": "user", "content": "done message"}]
        chunks.chat_files = [{"role": "assistant", "content": "chat file message"}]
        chunks.cur = [{"role": "user", "content": "current message"}]
        chunks.reminder = []

        # all_messages should contain repo message
        all_msgs = chunks.all_messages()
        self.assertIn(chunks.repo[0], all_msgs)

        # cacheable_messages should return everything up to and including the repo chunk
        cacheable = chunks.cacheable_messages()
        expected = chunks.system + chunks.repo  # prefix up to and including the cacheable repo chunk
        self.assertEqual(cacheable, expected)

        # Now verify behavior when there's no cache_control anywhere: should return full messages
        chunks2 = ChatChunks()
        chunks2.system = [{"role": "system", "content": "system prompt"}]
        # content is a list but lacks cache_control
        chunks2.repo = [
            {"role": "assistant", "content": [{"type": "text", "text": "repo data without control"}]}
        ]
        chunks2.done = [{"role": "user", "content": "done message"}]
        chunks2.chat_files = [{"role": "assistant", "content": "chat file message"}]
        chunks2.cur = [{"role": "user", "content": "current message"}]
        chunks2.reminder = []

        all_msgs2 = chunks2.all_messages()
        cacheable2 = chunks2.cacheable_messages()
        # Should return the full list unchanged
        self.assertEqual(cacheable2, all_msgs2)
