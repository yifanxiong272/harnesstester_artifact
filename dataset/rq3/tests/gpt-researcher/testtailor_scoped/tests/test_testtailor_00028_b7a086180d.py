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
        """Verify OpenAlexSearch constructor sets attributes from args and environment and enforces valid sort."""
        # Ensure environment variables are picked up
        with patch.dict(os.environ, {"OPENALEX_EMAIL": "tester@example.com", "OPENALEX_API_KEY": "apikey123"}):
            oa = OpenAlexSearch("sample query")
            self.assertEqual(oa.query, "sample query")
            # default sort must be the relevance_score one
            self.assertEqual(oa.sort, "relevance_score:desc")
            # environment values should be read into the instance
            self.assertEqual(oa.email, "tester@example.com")
            self.assertEqual(oa.api_key, "apikey123")

        # Valid explicit sort should be accepted
        oa2 = OpenAlexSearch("q2", sort="cited_by_count:desc")
        self.assertEqual(oa2.query, "q2")
        self.assertEqual(oa2.sort, "cited_by_count:desc")

        # Invalid sort should raise an AssertionError
        with self.assertRaises(AssertionError):
            OpenAlexSearch("bad", sort="not_a_valid_sort")
