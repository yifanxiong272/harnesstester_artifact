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
        """When examples is empty, add_cache_control_headers should add cache control to system messages."""
        chunks = ChatChunks()

        # Ensure examples is empty (default) and add a system message with string content
        chunks.examples = []
        chunks.system = [{"role": "system", "content": "initial system message"}]

        # Ensure other lists are empty so they don't interfere
        chunks.repo = []
        chunks.readonly_files = []
        chunks.chat_files = []

        # Call the method under test (this should hit the branch that calls add_cache_control(self.system))
        chunks.add_cache_control_headers()

        # The system message content should now be a list with a dict containing the converted text and cache_control
        self.assertIsInstance(chunks.system[-1]["content"], list)
        content = chunks.system[-1]["content"][0]
        self.assertIsInstance(content, dict)
        self.assertEqual(content.get("type"), "text")
        self.assertEqual(content.get("text"), "initial system message")
        self.assertEqual(content.get("cache_control"), {"type": "ephemeral"})
