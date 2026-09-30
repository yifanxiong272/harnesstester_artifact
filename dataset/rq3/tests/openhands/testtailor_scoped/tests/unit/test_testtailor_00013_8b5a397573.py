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
        """Test that a response with a single choice and a message without tool_calls
        is converted into a single MessageAction and that response_id is propagated.
        """
        # Minimal dummy objects to mimic the structure expected by response_to_actions
        class DummyMessage:
            def __init__(self, content):
                self.content = content

        class DummyChoice:
            def __init__(self, message):
                self.message = message

        class DummyResponse:
            def __init__(self, resp_id, choice):
                self.id = resp_id
                self.choices = [choice]

        # Create a response with one choice and a simple text message (no tool_calls)
        msg = DummyMessage("hello world")
        choice = DummyChoice(message=msg)
        response = DummyResponse("resp-123", choice)

        actions = response_to_actions(response)

        # Expect one action, which should be a MessageAction-like object
        self.assertEqual(len(actions), 1)
        action = actions[0]
        # The MessageAction produced by the function should carry the message content
        self.assertEqual(getattr(action, "content", None), "hello world")
        # It should also request waiting for a response
        self.assertTrue(getattr(action, "wait_for_response", False))
        # And the response_id should be set on the action
        self.assertEqual(getattr(action, "response_id", None), "resp-123")
