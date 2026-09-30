import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.views')
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
		"""Ensure success=True without is_done=True raises the expected ValueError and valid combos work."""
		# This should raise because success=True requires is_done=True
		with self.assertRaises(ValueError) as cm:
			ActionResult(is_done=False, success=True)
		self.assertIn('success=True can only be set when is_done=True', str(cm.exception))

		# This should not raise
		result = ActionResult(is_done=True, success=True)
		self.assertIsInstance(result, ActionResult)
		self.assertTrue(result.is_done)
		self.assertTrue(result.success)
