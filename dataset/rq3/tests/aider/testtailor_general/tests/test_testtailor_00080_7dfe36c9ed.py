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
        """Ensure add_cache_control_headers uses system when examples is empty."""
        chunks = ChatChunks()

        # ensure examples is empty so the branch takes the system path
        self.assertFalse(chunks.examples)

        # add a system message with string content (the code handles string -> dict)
        chunks.system.append({"role": "system", "content": "system prompt"})

        # leave repo, readonly_files, chat_files empty to avoid other effects
        self.assertFalse(chunks.repo)
        self.assertFalse(chunks.readonly_files)
        self.assertFalse(chunks.chat_files)

        # call the method under test
        chunks.add_cache_control_headers()

        # the last system message content should now be a list with a dict containing cache_control
        last_content = chunks.system[-1]["content"]
        self.assertIsInstance(last_content, list)
        self.assertIsInstance(last_content[0], dict)
        self.assertEqual(last_content[0].get("type"), "text")
        self.assertEqual(last_content[0].get("text"), "system prompt")
        self.assertIn("cache_control", last_content[0])
        self.assertEqual(last_content[0]["cache_control"].get("type"), "ephemeral")
