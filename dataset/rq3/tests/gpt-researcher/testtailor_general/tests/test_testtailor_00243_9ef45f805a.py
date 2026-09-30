import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.xquik.xquik')
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
        """Ensure get_api_key returns the XQUIK_API_KEY environment variable when set."""
        # Set the environment variable that XquikSearch expects.
        os.environ["XQUIK_API_KEY"] = "dummy_key_123"
        try:
            # Instantiating XquikSearch calls get_api_key() in __init__, so this should succeed.
            search = XquikSearch(query="test query")
            # get_api_key should return the same value and it should be stored on the instance.
            self.assertEqual(search.get_api_key(), "dummy_key_123")
            self.assertEqual(search.api_key, "dummy_key_123")
        finally:
            # Clean up environment to avoid side effects on other tests.
            del os.environ["XQUIK_API_KEY"]
