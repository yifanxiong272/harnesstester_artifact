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
        """Test SerpApiSearch __init__ assigns query, handles query_domains, and reads API key from env."""
        # Preserve existing env var and restore later
        prev = os.environ.get("SERPAPI_API_KEY")
        try:
            os.environ["SERPAPI_API_KEY"] = "dummy_key_123"

            query = "sample query"
            domains = ["example.com", "test.com"]
            s = SerpApiSearch(query, query_domains=domains)

            # Verify attributes set correctly
            self.assertEqual(s.query, query)
            self.assertEqual(s.query_domains, domains)
            self.assertEqual(s.api_key, "dummy_key_123")

            # When an empty list (falsy) is passed, query_domains should become None
            s2 = SerpApiSearch("other query", query_domains=[])
            self.assertEqual(s2.query, "other query")
            self.assertIsNone(s2.query_domains)
            self.assertEqual(s2.api_key, "dummy_key_123")
        finally:
            # Restore previous environment state
            if prev is None:
                os.environ.pop("SERPAPI_API_KEY", None)
            else:
                os.environ["SERPAPI_API_KEY"] = prev
