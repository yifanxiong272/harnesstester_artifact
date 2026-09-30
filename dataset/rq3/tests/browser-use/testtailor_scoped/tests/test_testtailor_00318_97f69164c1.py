import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.tools.service')
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
		"""When BrowserError has long_term_memory and no short_term_memory,
		handle_browser_error should return an ActionResult that contains the long_term_memory
		as the error and does not include extracted_content.
		"""
		# Prepare a BrowserError with long_term_memory set and short_term_memory unset
		err_long = "persistent error info for LLM"
		e = BrowserError(message="something went wrong", long_term_memory=err_long, short_term_memory=None)

		# Call the function under test
		result = handle_browser_error(e)

		# Verify we got an ActionResult with the long_term_memory as the error
		self.assertIsInstance(result, ActionResult)
		self.assertEqual(result.error, err_long)

		# Ensure no extracted content was included and flags are default
		self.assertIsNone(result.extracted_content)
		self.assertFalse(result.include_extracted_content_only_once)
