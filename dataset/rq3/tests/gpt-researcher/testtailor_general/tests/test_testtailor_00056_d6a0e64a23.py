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
        """Verify BingSearch __init__ sets attributes and calls get_api_key"""
        # Patch get_api_key so we don't rely on environment variables
        with patch.object(BingSearch, "get_api_key", return_value="fake_key") as mock_get_api:
            # Provide explicit query_domains
            bs = BingSearch(query="search term", query_domains=["example.com"])
            # Verify attributes set correctly
            self.assertEqual(bs.query, "search term")
            self.assertEqual(bs.query_domains, ["example.com"])
            self.assertEqual(bs.api_key, "fake_key")
            # Logger should be present and have typical logging methods
            self.assertIsNotNone(bs.logger)
            self.assertTrue(hasattr(bs.logger, "error"))
            self.assertTrue(hasattr(bs.logger, "info"))

            # Create another instance without query_domains to exercise the "or None" assignment
            bs2 = BingSearch(query="another term")
            self.assertEqual(bs2.query, "another term")
            self.assertIsNone(bs2.query_domains)
            self.assertEqual(bs2.api_key, "fake_key")
            self.assertIsNotNone(bs2.logger)

            # Ensure get_api_key was called for each initialization
            self.assertEqual(mock_get_api.call_count, 2)
