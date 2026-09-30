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
        """Verify SerpApiSearch sets query, normalizes query_domains, and uses get_api_key."""
        # Patch get_api_key so the constructor doesn't read environment variables
        with patch.object(SerpApiSearch, "get_api_key", return_value="FAKE_KEY") as mock_get_api:
            # Case 1: provide a list of domains
            s = SerpApiSearch(query="search term", query_domains=["example.com", "another.com"])
            self.assertEqual(s.query, "search term")
            self.assertEqual(s.query_domains, ["example.com", "another.com"])
            self.assertEqual(s.api_key, "FAKE_KEY")

            # Case 2: provide an empty list -> should be normalized to None
            s_empty = SerpApiSearch(query="other", query_domains=[])
            self.assertEqual(s_empty.query, "other")
            self.assertIsNone(s_empty.query_domains)
            self.assertEqual(s_empty.api_key, "FAKE_KEY")

            # Case 3: omit query_domains (default)
            s_none = SerpApiSearch(query="third")
            self.assertEqual(s_none.query, "third")
            self.assertIsNone(s_none.query_domains)
            self.assertEqual(s_none.api_key, "FAKE_KEY")

            # Ensure get_api_key was invoked for each instantiation
            self.assertEqual(mock_get_api.call_count, 3)
