import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.searx.searx')
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
        """Test SearxSearch __init__ sets attributes and uses get_searxng_url."""
        # Patch get_searxng_url to avoid relying on environment variables
        with patch.object(SearxSearch, "get_searxng_url", return_value="https://searx.example/") as mock_get_url:
            # When query_domains is provided, it should be preserved
            s = SearxSearch(query="test query", query_domains=["example.com"])
            self.assertEqual(s.query, "test query")
            self.assertEqual(s.query_domains, ["example.com"])
            self.assertEqual(s.base_url, "https://searx.example/")
            self.assertTrue(mock_get_url.called)

            # Reset mock and test falsy query_domains (e.g., empty list) becomes None
            mock_get_url.reset_mock()
            s2 = SearxSearch(query="another query", query_domains=[])
            self.assertEqual(s2.query, "another query")
            self.assertIsNone(s2.query_domains)
            self.assertEqual(s2.base_url, "https://searx.example/")
            mock_get_url.assert_called_once()
