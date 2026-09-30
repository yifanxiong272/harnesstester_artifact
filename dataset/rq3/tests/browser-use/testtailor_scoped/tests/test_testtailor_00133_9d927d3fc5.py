import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.google.serializer')
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
        """System message with iterable text content parts should be combined into system_message."""
        from browser_use.llm.google.chat import GoogleMessageSerializer
        from browser_use.llm.messages import SystemMessage

        # Provide content as a list of text parts (dicts with type 'text').
        content_parts = [
            {"type": "text", "text": "system line one"},
            {"type": "text", "text": "system line two"},
        ]

        sys_msg = SystemMessage(content=content_parts)

        formatted_messages, system_message = GoogleMessageSerializer.serialize_messages([sys_msg])

        # System message should be the joined text parts; no conversation messages returned
        self.assertEqual(system_message, "system line one\nsystem line two")
        self.assertEqual(formatted_messages, [])
