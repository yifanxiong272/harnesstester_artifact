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
		"""SystemMessage with string content should be extracted as system_message when include_system_in_user=False"""
		from browser_use.llm.google.chat import GoogleMessageSerializer
		from browser_use.llm.messages import SystemMessage

		sys_text = "System instruction: Be concise."
		messages = [SystemMessage(content=sys_text)]

		formatted_messages, system_message = GoogleMessageSerializer.serialize_messages(messages, include_system_in_user=False)

		# Since the only message is a system message and include_system_in_user is False,
		# there should be no formatted conversation messages and the system_message should be extracted.
		self.assertEqual(formatted_messages, [])
		self.assertEqual(system_message, sys_text)
