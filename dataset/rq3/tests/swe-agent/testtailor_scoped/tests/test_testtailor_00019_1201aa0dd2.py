import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.history_processors')
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
        """Verify _set_content_text updates the inner text when content is a single-message list."""
        # entry['content'] is a list with a single message dict (not a string),
        # so the branch that sets entry['content'][0]['text'] should be taken.
        entry = {"content": [{"text": "original"}], "message_type": "observation"}
        _set_content_text(entry, "new text")
        # Confirm the inner text was updated and the list structure is preserved.
        self.assertIsInstance(entry["content"], list)
        self.assertEqual(len(entry["content"]), 1)
        self.assertEqual(entry["content"][0]["text"], "new text")
