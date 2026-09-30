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
	def test_system_message_included_in_first_user_when_flag_true(self):
		"""When include_system_in_user is True and a SystemMessage with string content is present,
		the system content should be prepended to the first user message and no separate system_message returned.
		"""
		# Create a system message with string content and a following user message
		system_msg = SystemMessage(content="System instruction")
		user_msg = UserMessage(content="Hello user")

		# Call the serializer with include_system_in_user=True to trigger system_parts.append(...)
		formatted_messages, system_message = GoogleMessageSerializer.serialize_messages(
			[m for m in (system_msg, user_msg)], include_system_in_user=True
		)

		# When included in user, serializer should return None for system_message
		self.assertIsNone(system_message)

		# There should be one formatted message (the user message with prepended system text)
		self.assertEqual(len(formatted_messages), 1)
		first = formatted_messages[0]

		# Role should be 'user' and the text part should contain system + user separated by two newlines
		self.assertEqual(first.role, 'user')
		# The first part should be a text part with the combined content
		self.assertEqual(first.parts[0].text, "System instruction\n\nHello user")
