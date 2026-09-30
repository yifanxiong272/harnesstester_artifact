import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.google.google')
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
        """Verify get_cx_key returns the GOOGLE_CX_KEY environment variable value."""
        # Ensure env var is set for the test and provide a dummy API key to avoid get_api_key being called
        os.environ["GOOGLE_CX_KEY"] = "test-cx-key"
        headers = {"google_api_key": "dummy-api-key"}
        try:
            gs = GoogleSearch(query="dummy query", headers=headers)
            # __init__ should have called get_cx_key and populated cx_key
            self.assertEqual(gs.cx_key, "test-cx-key")
            # calling the method directly should also return the same value
            self.assertEqual(gs.get_cx_key(), "test-cx-key")
        finally:
            # Clean up environment
            del os.environ["GOOGLE_CX_KEY"]
