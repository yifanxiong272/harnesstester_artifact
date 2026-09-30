import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.message_manager.service')
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
        """Verify _log_get_message_emoji returns correct emoji for message class names and a default."""
        # Create simple dynamic classes with the target names so __class__.__name__ matches
        UserMessage = type('UserMessage', (), {})  # should map to 💬
        SystemMessage = type('SystemMessage', (), {})  # should map to 🧠
        AssistantMessage = type('AssistantMessage', (), {})  # should map to 🔨
        UnknownMessage = type('SomeOtherMessage', (), {})  # should map to default 🎮

        user_msg = UserMessage()
        system_msg = SystemMessage()
        assistant_msg = AssistantMessage()
        unknown_msg = UnknownMessage()

        self.assertEqual(_log_get_message_emoji(user_msg), '💬')
        self.assertEqual(_log_get_message_emoji(system_msg), '🧠')
        self.assertEqual(_log_get_message_emoji(assistant_msg), '🔨')
        self.assertEqual(_log_get_message_emoji(unknown_msg), '🎮')
