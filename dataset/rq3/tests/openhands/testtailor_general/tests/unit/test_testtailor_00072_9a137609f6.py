import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.agenthub.loc_agent.function_calling')
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
        """Response with a single choice and no tool_calls should produce a MessageAction."""
        # Create lightweight objects without importing SimpleNamespace
        class Obj:
            pass

        response = Obj()
        response.id = 'resp-1'

        choice = Obj()
        message = Obj()
        message.content = 'hello'  # No tool_calls attribute -> triggers MessageAction branch
        choice.message = message

        response.choices = [choice]

        actions = response_to_actions(response)

        # Expect exactly one action created
        self.assertEqual(len(actions), 1)
        action = actions[0]

        # The MessageAction should carry the message content and wait_for_response should be True
        self.assertEqual(action.content, 'hello')
        self.assertTrue(getattr(action, 'wait_for_response', False))

        # The response id should be attached to the action
        self.assertEqual(action.response_id, 'resp-1')
