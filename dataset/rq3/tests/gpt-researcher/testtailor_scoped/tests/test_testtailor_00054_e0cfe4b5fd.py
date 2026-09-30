import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.arxiv.arxiv')
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
        """Verify ArxivSearch __init__ uses module-global 'arxiv', sets query, and selects correct SortCriterion or raises on invalid sort."""
        # Create a fake arxiv with SortCriterion values
        class _FakeSort:
            pass
        _FakeSort.Relevance = object()
        _FakeSort.SubmittedDate = object()

        class _FakeArxiv:
            SortCriterion = _FakeSort

        # Inject fake arxiv into the globals of ArxivSearch.__init__
        # (This patches the name 'arxiv' that the constructor references)
        ArxivSearch.__init__.__globals__['arxiv'] = _FakeArxiv

        # Construct with default/Relevance sort
        inst1 = ArxivSearch(query="test-query", sort='Relevance')
        # self.arxiv should reference the injected fake arxiv
        self.assertIs(inst1.arxiv, _FakeArxiv)
        # query should be preserved
        self.assertEqual(inst1.query, "test-query")
        # sort should be set to the fake Relevance enum/value
        self.assertIs(inst1.sort, _FakeSort.Relevance)

        # Construct with SubmittedDate sort
        inst2 = ArxivSearch(query="other-query", sort='SubmittedDate')
        self.assertIs(inst2.sort, _FakeSort.SubmittedDate)

        # Invalid sort string should trigger the assertion
        with self.assertRaises(AssertionError):
            ArxivSearch(query="bad", sort='NotAValidSort')
