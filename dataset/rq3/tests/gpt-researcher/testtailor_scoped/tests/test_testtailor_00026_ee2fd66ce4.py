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
        """Verify BingSearch __init__ sets query, normalizes query_domains, obtains API key and creates a logger."""
        # Ensure a predictable API key is available for get_api_key
        os.environ["BING_API_KEY"] = "testkey123"
        try:
            # Non-empty query_domains should be preserved
            bs = BingSearch(query="sample query", query_domains=["example.com"])
            self.assertEqual(bs.query, "sample query")
            self.assertEqual(bs.query_domains, ["example.com"])
            self.assertEqual(bs.api_key, "testkey123")
            self.assertIsInstance(bs.logger, logging.Logger)

            # Empty list for query_domains should be normalized to None
            bs_empty = BingSearch(query="another query", query_domains=[])
            self.assertEqual(bs_empty.query, "another query")
            self.assertIsNone(bs_empty.query_domains)
            self.assertEqual(bs_empty.api_key, "testkey123")
            self.assertIsInstance(bs_empty.logger, logging.Logger)

            # Omitting query_domains (default) should result in None
            bs_default = BingSearch(query="third query")
            self.assertEqual(bs_default.query, "third query")
            self.assertIsNone(bs_default.query_domains)
            self.assertEqual(bs_default.api_key, "testkey123")
            self.assertIsInstance(bs_default.logger, logging.Logger)
        finally:
            # Clean up environment change
            del os.environ["BING_API_KEY"]
