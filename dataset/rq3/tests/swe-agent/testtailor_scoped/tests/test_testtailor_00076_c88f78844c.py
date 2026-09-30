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
        """Ensure no tags are added when an action has no tool_calls (empty list)."""
        processor = TagToolCallObservations(tags={"test"}, function_names={"edit"})
        # history contains an action that would match by action text, but has no tool_calls
        history = [
            {"message_type": "action", "action": "edit file.txt", "tool_calls": []}
        ]
        new_history = processor(history)
        for entry in new_history:
            if entry.get("action", "").startswith("edit "):
                # since tool_calls is empty, tags should not be added
                self.assertNotIn("test", entry.get("tags", []), entry)
