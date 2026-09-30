import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.bocha.bocha')
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
        """Verify BoChaSearch initializes query, query_domains, and reads BOCHA_API_KEY from env."""
        # Preserve original environment value
        original_key = os.environ.get("BOCHA_API_KEY")
        try:
            # Set a test API key so constructor can read it
            os.environ["BOCHA_API_KEY"] = "test_key_123"

            # Case 1: No query_domains provided -> should be None
            b1 = BoChaSearch("search term")
            self.assertEqual(b1.query, "search term")
            self.assertIsNone(b1.query_domains)
            self.assertEqual(b1.api_key, "test_key_123")

            # Case 2: Empty list provided -> due to `query_domains = query_domains or None` becomes None
            b2 = BoChaSearch("another query", query_domains=[])
            self.assertEqual(b2.query, "another query")
            self.assertIsNone(b2.query_domains)

            # Case 3: Non-empty list should be preserved
            domains = ["example.com", "test.org"]
            b3 = BoChaSearch("third query", query_domains=domains)
            self.assertEqual(b3.query, "third query")
            self.assertEqual(b3.query_domains, domains)
            self.assertEqual(b3.api_key, "test_key_123")
        finally:
            # Restore original environment
            if original_key is None:
                del os.environ["BOCHA_API_KEY"]
            else:
                os.environ["BOCHA_API_KEY"] = original_key
