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
        """Test XquikSearch.__init__ assigns query, query_domains and calls get_api_key."""
        with patch.object(XquikSearch, "get_api_key", return_value="FAKE_API_KEY") as mock_get:
            instance = XquikSearch(query="test-query", query_domains=["example.com", "another.com"])
            # Verify attributes set correctly
            self.assertEqual(instance.query, "test-query")
            self.assertEqual(instance.query_domains, ["example.com", "another.com"])
            self.assertEqual(instance.api_key, "FAKE_API_KEY")
            # Ensure get_api_key was invoked during initialization
            mock_get.assert_called_once()
