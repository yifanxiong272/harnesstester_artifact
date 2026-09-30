import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.serpapi.serpapi')
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
        """Ensure SerpApiSearch raises a clear error when SERPAPI_API_KEY is not set."""
        # Remove the environment variable if present and restore it after the test
        original_value = os.environ.pop("SERPAPI_API_KEY", None)
        try:
            with self.assertRaises(Exception) as cm:
                SerpApiSearch("dummy query")
            self.assertIn("SerpApi API key not found", str(cm.exception))
            self.assertIn("SERPAPI_API_KEY", str(cm.exception))
        finally:
            if original_value is not None:
                os.environ["SERPAPI_API_KEY"] = original_value
