import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.openalex.openalex')
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
        """Verify constructor sets query, validates sort, and reads env vars for email/api_key."""
        # Preserve original environment values to restore after test
        original_email = os.environ.get("OPENALEX_EMAIL")
        original_api_key = os.environ.get("OPENALEX_API_KEY")
        try:
            # Set environment variables expected to be read by constructor
            os.environ["OPENALEX_EMAIL"] = "tester@example.com"
            os.environ["OPENALEX_API_KEY"] = "TEST_API_KEY_123"

            # Valid sort: should not raise and should set attributes correctly
            s = OpenAlexSearch(query="machine learning", sort="cited_by_count:desc")
            self.assertEqual(s.query, "machine learning")
            self.assertEqual(s.sort, "cited_by_count:desc")
            self.assertEqual(s.email, "tester@example.com")
            self.assertEqual(s.api_key, "TEST_API_KEY_123")

            # Default sort parameter when not provided
            s_default = OpenAlexSearch(query="deep learning")
            self.assertEqual(s_default.query, "deep learning")
            self.assertEqual(s_default.sort, OpenAlexSearch.VALID_SORT_CRITERIA[0])

            # Invalid sort should trigger the assertion
            with self.assertRaises(AssertionError):
                OpenAlexSearch(query="bad sort", sort="not_a_valid_sort")
        finally:
            # Restore original environment state
            if original_email is None:
                os.environ.pop("OPENALEX_EMAIL", None)
            else:
                os.environ["OPENALEX_EMAIL"] = original_email

            if original_api_key is None:
                os.environ.pop("OPENALEX_API_KEY", None)
            else:
                os.environ["OPENALEX_API_KEY"] = original_api_key
