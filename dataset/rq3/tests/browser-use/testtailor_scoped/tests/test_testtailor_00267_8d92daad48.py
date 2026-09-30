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
        """When BrowserError contains both short_term_memory and long_term_memory,
        handle_browser_error should return an ActionResult with extracted_content set
        to short_term_memory, error set to long_term_memory, and include_extracted_content_only_once True.
        """
        # Construct a BrowserError with both memories set
        err = BrowserError(
            message="Test browser failure",
            short_term_memory="temporary context shown once",
            long_term_memory="persistent error info"
        )

        # Call the function under test
        result = handle_browser_error(err)

        # Verify the returned object and its fields
        self.assertIsInstance(result, ActionResult)
        self.assertEqual(result.extracted_content, "temporary context shown once")
        self.assertEqual(result.error, "persistent error info")
        self.assertTrue(result.include_extracted_content_only_once)
