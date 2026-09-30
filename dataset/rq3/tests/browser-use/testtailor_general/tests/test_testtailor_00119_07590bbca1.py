import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.observability')
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
		"""Verify _is_debug_mode respects the LMNR_LOGGING_LEVEL env var (case-insensitive exact match to 'debug')."""
		# Preserve existing value
		original = os.environ.get('LMNR_LOGGING_LEVEL', None)
		try:
			# If not set -> False
			os.environ.pop('LMNR_LOGGING_LEVEL', None)
			self.assertFalse(_is_debug_mode(), "Unset LMNR_LOGGING_LEVEL should not enable debug mode")

			# Exact 'debug' (lowercase) -> True
			os.environ['LMNR_LOGGING_LEVEL'] = 'debug'
			self.assertTrue(_is_debug_mode(), "'debug' should enable debug mode")

			# Uppercase -> True because of .lower()
			os.environ['LMNR_LOGGING_LEVEL'] = 'DEBUG'
			self.assertTrue(_is_debug_mode(), "'DEBUG' should enable debug mode after lowercasing")

			# Mixed case -> True
			os.environ['LMNR_LOGGING_LEVEL'] = 'DeBuG'
			self.assertTrue(_is_debug_mode(), "Mixed-case 'DeBuG' should enable debug mode after lowercasing")

			# Leading/trailing whitespace matters because code does not strip -> should be False
			os.environ['LMNR_LOGGING_LEVEL'] = ' debug '
			self.assertFalse(_is_debug_mode(), "Whitespace around 'debug' should NOT enable debug mode (no strip)")

			# Different value -> False
			os.environ['LMNR_LOGGING_LEVEL'] = 'info'
			self.assertFalse(_is_debug_mode(), "'info' should not enable debug mode")

			# Empty string -> False
			os.environ['LMNR_LOGGING_LEVEL'] = ''
			self.assertFalse(_is_debug_mode(), "Empty LMNR_LOGGING_LEVEL should not enable debug mode")
		finally:
			# Restore original environment state
			if original is None:
				os.environ.pop('LMNR_LOGGING_LEVEL', None)
			else:
				os.environ['LMNR_LOGGING_LEVEL'] = original
