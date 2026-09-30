import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.memory.conversation_memory')
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
        """User-sourced action (in allowed tuple) with no tool metadata returns the simple user message."""
        # Import the package dynamically to avoid top-level import statements
        openhands = __import__('openhands')

        # Build a ConversationMemory with a minimal config (prompt_manager not needed for this test)
        AgentConfig = openhands.core.config.AgentConfig
        ConversationMemory = openhands.memory.conversation_memory.ConversationMemory
        conv = ConversationMemory(config=AgentConfig(), prompt_manager=None)

        # Create an MCPAction (one of the action types checked in the tuple)
        MCPAction = openhands.events.action.mcp.MCPAction
        action = MCPAction(name='read_file')
        # Mark the action as coming from the user
        EventSource = openhands.events.event.EventSource
        action._source = EventSource.USER
        # Ensure tool_call_metadata is None to trigger the branch
        action.tool_call_metadata = None

        pending: dict[str, openhands.core.message.Message] = {}
        messages = conv._process_action(
            action=action,
            pending_tool_call_action_messages=pending,
            vision_is_active=False,
        )

        # Verify we got the expected single user message with the exact formatted text
        self.assertIsInstance(messages, list)
        self.assertEqual(len(messages), 1)
        msg = messages[0]
        self.assertEqual(msg.role, 'user')
        self.assertTrue(len(msg.content) > 0)
        # The first content item should be TextContent with the expected text
        first_content = msg.content[0]
        TextContent = openhands.core.message.TextContent
        self.assertIsInstance(first_content, TextContent)
        expected_text = f'User requested to read file: {str(action)}'
        self.assertEqual(first_content.text, expected_text)
