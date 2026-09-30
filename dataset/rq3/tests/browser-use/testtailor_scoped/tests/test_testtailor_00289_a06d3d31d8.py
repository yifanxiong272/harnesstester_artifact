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
		"""System message with iterable content parts is appended to system_parts when include_system_in_user=True"""
		# Create a SystemMessage whose content is a list of text parts (not a plain string)
		system_parts = [
			{'type': 'text', 'text': 'System instruction A'},
			{'type': 'text', 'text': 'System instruction B'},
		]
		system_msg = SystemMessage(content=system_parts)

		# First user message should receive the system parts prepended when include_system_in_user=True
		user_msg = UserMessage(content='Hello user')

		# Call the serializer
		formatted_messages, system_message = GoogleMessageSerializer.serialize_messages(
			[m for m in (system_msg, user_msg)], include_system_in_user=True
		)

		# Because include_system_in_user=True, the system message should NOT be returned separately
		self.assertIsNone(system_message)

		# One formatted message should be produced (the user message with system text prepended)
		self.assertEqual(len(formatted_messages), 1)
		content = formatted_messages[0]

		# Role should be 'user'
		self.assertEqual(content.role, 'user')

		# The first part's text should contain the combined system parts joined by '\n'
		# followed by two newlines and the original user content
		expected_system_combined = 'System instruction A\nSystem instruction B'
		expected_text = f'{expected_system_combined}\n\nHello user'

		# Ensure the part text matches expected
		self.assertTrue(len(content.parts) >= 1)
		self.assertEqual(content.parts[0].text, expected_text)
