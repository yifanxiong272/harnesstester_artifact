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
        """Ensure get_api_key returns the BING_API_KEY environment variable when set."""
        prev = os.environ.get("BING_API_KEY")
        try:
            os.environ["BING_API_KEY"] = "dummy_key_123"
            bs = BingSearch(query="test query")
            # api_key is set during __init__ via get_api_key()
            self.assertEqual(bs.api_key, "dummy_key_123")
            # calling get_api_key directly should also return the same value
            self.assertEqual(bs.get_api_key(), "dummy_key_123")
        finally:
            # restore previous environment state
            if prev is None:
                if "BING_API_KEY" in os.environ:
                    del os.environ["BING_API_KEY"]
            else:
                os.environ["BING_API_KEY"] = prev
