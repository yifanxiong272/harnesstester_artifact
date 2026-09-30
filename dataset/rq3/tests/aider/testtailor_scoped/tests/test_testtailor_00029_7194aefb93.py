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
        """When examples is present, add_cache_control_headers should call add_cache_control on examples
        and set the cache_control type to ephemeral on the last example message."""
        chunks = ChatChunks()

        # prepare an examples list with a single message whose content is a plain string
        chunks.examples = [{"role": "user", "content": "example content"}]
        # ensure other branches do nothing (keep them empty)
        chunks.repo = []
        chunks.readonly_files = []
        chunks.chat_files = []

        # call the method under test
        chunks.add_cache_control_headers()

        # verify the examples last message content was transformed into a list with cache_control
        content = chunks.examples[-1]["content"]
        self.assertIsInstance(content, list)
        self.assertIsInstance(content[0], dict)
        self.assertIn("cache_control", content[0])
        self.assertEqual(content[0]["cache_control"], {"type": "ephemeral"})
        # original text should be preserved under "text"
        self.assertEqual(content[0].get("text"), "example content")
        # other lists should remain empty as set
        self.assertEqual(chunks.repo, [])
        self.assertEqual(chunks.readonly_files, [])
        self.assertEqual(chunks.chat_files, [])
