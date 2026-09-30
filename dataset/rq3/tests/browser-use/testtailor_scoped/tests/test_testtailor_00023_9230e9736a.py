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
		"""System message string is appended to first user message when include_system_in_user=True."""
		# Import inside the test to avoid top-level import statements per instructions
		from browser_use.llm.google.serializer import GoogleMessageSerializer
		from browser_use.llm.messages import SystemMessage, UserMessage

		# Prepare messages: a system message (string content) followed by a user message
		sys_text = 'System instruction'
		user_text = 'Hello user'
		messages = [SystemMessage(content=sys_text), UserMessage(content=user_text)]

		# Call the serializer with include_system_in_user=True to trigger system_parts.append(message.content)
		formatted_messages, system_message = GoogleMessageSerializer.serialize_messages(messages, include_system_in_user=True)

		# When include_system_in_user=True, system_message should be None and the system text
		# should be prepended to the first user message with two newlines separating parts.
		self.assertIsNone(system_message)
		self.assertEqual(len(formatted_messages), 1)

		content = formatted_messages[0]
		self.assertEqual(content.role, 'user')
		# Expect a single Part containing the combined system + user text
		self.assertEqual(len(content.parts), 1)
		part = content.parts[0]
		# Part should expose the combined text
		expected_text = f'{sys_text}\n\n{user_text}'
		# Use getattr to be tolerant if attribute naming varies; most implementations expose .text
		self.assertEqual(getattr(part, 'text'), expected_text)
