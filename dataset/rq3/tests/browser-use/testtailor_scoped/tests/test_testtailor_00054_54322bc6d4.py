import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.message_manager.views')
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
		"""Ensure HistoryItem raises when both error and system_message are provided"""
		with self.assertRaises(ValueError) as cm:
			# Both fields set should trigger the model_post_init validation
			HistoryItem(step_number=1, error='an error', system_message='a system message')

		self.assertIn('Cannot have both error and system_message at the same time', str(cm.exception))
