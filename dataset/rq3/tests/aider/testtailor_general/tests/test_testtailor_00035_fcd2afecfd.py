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
        """Ensure add_cache_control_headers marks examples as cacheable (calls add_cache_control on examples)."""
        # Case 1: message content is a plain string
        chunks = ChatChunks()
        chunks.examples = [{"role": "assistant", "content": "plain text content"}]

        # Sanity before call
        self.assertIsInstance(chunks.examples, list)
        self.assertEqual(chunks.examples[-1]["content"], "plain text content")

        # Exercise target: should take the branch `if self.examples` and call add_cache_control(self.examples)
        chunks.add_cache_control_headers()

        # After calling, the last example's content should be a list with a dict that contains cache_control
        updated = chunks.examples[-1]["content"]
        self.assertIsInstance(updated, list)
        self.assertIsInstance(updated[0], dict)
        self.assertIn("cache_control", updated[0])
        self.assertEqual(updated[0]["cache_control"], {"type": "ephemeral"})
        # For a string input, add_cache_control converts it to type="text" with text field
        self.assertEqual(updated[0]["type"], "text")
        self.assertEqual(updated[0]["text"], "plain text content")

        # Case 2: message content is already a dict
        chunks2 = ChatChunks()
        chunks2.examples = [{"role": "assistant", "content": {"type": "text", "text": "dict content"}}]

        # Exercise target again
        chunks2.add_cache_control_headers()

        updated2 = chunks2.examples[-1]["content"]
        self.assertIsInstance(updated2, list)
        self.assertIsInstance(updated2[0], dict)
        # Existing dict should now include cache_control as well
        self.assertIn("cache_control", updated2[0])
        self.assertEqual(updated2[0]["cache_control"], {"type": "ephemeral"})
        self.assertEqual(updated2[0]["text"], "dict content")
        self.assertEqual(updated2[0]["type"], "text")
