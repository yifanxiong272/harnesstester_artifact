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
        """Ensure no tags are added when an action entry has no tool_calls (hits `if not function_calls: return False`)."""
        processor = TagToolCallObservations(tags={"test"}, function_names={"edit"})
        history = [
            {"message_type": "action", "action": "do_something", "content": "an action with no tool calls", "tool_calls": []}
        ]
        new_history = processor(history)
        # since there are no tool_calls, tags should not be added
        self.assertNotIn("tags", new_history[0])
