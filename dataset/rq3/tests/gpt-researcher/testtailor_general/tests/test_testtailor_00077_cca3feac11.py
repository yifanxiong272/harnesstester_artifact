import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.semantic_scholar.semantic_scholar')
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
        """Verify __init__ assigns query, enforces valid sort, and lowercases the sort value."""
        # Valid sort criterion (camelCase) should be accepted and stored lowercased
        s = SemanticScholarSearch(query="deep learning", sort="citationCount")
        self.assertEqual(s.query, "deep learning")
        self.assertEqual(s.sort, "citationcount")  # stored as lowercased

        # Another valid sort
        s2 = SemanticScholarSearch(query="nlp", sort="relevance")
        self.assertEqual(s2.query, "nlp")
        self.assertEqual(s2.sort, "relevance")

        # Invalid sort should raise an AssertionError
        with self.assertRaises(AssertionError):
            SemanticScholarSearch(query="test", sort="invalidSort")
