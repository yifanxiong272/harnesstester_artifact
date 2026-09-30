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
		"""SystemMessage with string content should be extracted as system_message when include_system_in_user is False"""
		from browser_use.llm.google.serializer import GoogleMessageSerializer
		from browser_use.llm.messages import SystemMessage

		system_text = "This is a system instruction."
		msg = SystemMessage(content=system_text)

		formatted_messages, system_message = GoogleMessageSerializer.serialize_messages([msg], include_system_in_user=False)

		# system_message should be extracted and formatted_messages should be empty
		self.assertEqual(system_message, system_text)
		self.assertEqual(formatted_messages, [])
