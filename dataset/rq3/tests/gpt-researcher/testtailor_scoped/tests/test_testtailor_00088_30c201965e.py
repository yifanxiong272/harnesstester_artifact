import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.bing.bing')
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
        """Verify BingSearch raises when BING_API_KEY missing and returns when present."""
        # Ensure environment variable is not set to trigger the exception path
        prev = os.environ.pop("BING_API_KEY", None)
        try:
            with self.assertRaises(Exception) as cm:
                _ = BingSearch("test query")
            self.assertIn("Bing API key not found. Please set the BING_API_KEY environment variable.", str(cm.exception))

            # Now set the environment variable and ensure get_api_key succeeds via __init__
            os.environ["BING_API_KEY"] = "dummy_key_123"
            bs = BingSearch("test query")
            self.assertEqual(bs.api_key, "dummy_key_123")
        finally:
            # Restore previous environment state
            if prev is None:
                os.environ.pop("BING_API_KEY", None)
            else:
                os.environ["BING_API_KEY"] = prev
