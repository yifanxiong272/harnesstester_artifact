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
        """_log_get_message_emoji returns mapped emoji for known message classes and default for others."""
        # Create lightweight dummy instances whose class names match the expected message class names.
        user_msg = type('UserMessage', (), {})()
        system_msg = type('SystemMessage', (), {})()
        assistant_msg = type('AssistantMessage', (), {})()

        # An unknown message type should yield the default emoji.
        unknown_msg = type('SomeOtherMessage', (), {})()

        # A subclass with a different class name should also yield the default emoji.
        user_subclass_msg = type('UserMessageSubclass', (), {})()

        self.assertEqual(_log_get_message_emoji(user_msg), '💬')
        self.assertEqual(_log_get_message_emoji(system_msg), '🧠')
        self.assertEqual(_log_get_message_emoji(assistant_msg), '🔨')

        self.assertEqual(_log_get_message_emoji(unknown_msg), '🎮')
        self.assertEqual(_log_get_message_emoji(user_subclass_msg), '🎮')
