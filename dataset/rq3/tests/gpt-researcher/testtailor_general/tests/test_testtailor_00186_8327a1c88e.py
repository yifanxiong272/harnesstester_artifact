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
        """Verify ArxivSearch.search builds results from arxiv.Client().results(...) without raising"""
        # Instantiate the ArxivSearch (assumes ArxivSearch symbol is available in the test module)
        searcher = ArxivSearch(query="quantum")

        # Create a simple SortCriterion-like object
        class DummySort:
            Relevance = "relevance"
            SubmittedDate = "submitted"

        # Prepare a fake result object returned by Client().results(...)
        fake_result = MagicMock()
        fake_result.title = "Test Paper"
        fake_result.pdf_url = "http://example.com/paper.pdf"
        fake_result.summary = "This is a summary."

        # fake client that returns an iterator over results
        fake_client = MagicMock()
        fake_client.results.return_value = iter([fake_result])

        # Create a fake arxiv module object where Search returns an object with needed attributes
        def make_search_obj(query, max_results, sort_by):
            class DummySearchObj:
                def __init__(self, query, max_results, sort_by):
                    self.query = query
                    self.max_results = max_results
                    self.sort_by = sort_by
            return DummySearchObj(query, max_results, sort_by)

        fake_arxiv = MagicMock()
        fake_arxiv.SortCriterion = DummySort
        # Use MagicMock for Search so we can assert calls, but have it return an object with attributes expected by real Client.results
        fake_arxiv.Search = MagicMock(side_effect=make_search_obj)
        fake_arxiv.Client = MagicMock(return_value=fake_client)

        # Inject the fake arxiv into the module where ArxivSearch is defined so the function's "arxiv.Client()" call uses it.
        mod = __import__(searcher.__class__.__module__, fromlist=['*'])
        setattr(mod, 'arxiv', fake_arxiv)

        # Also ensure the instance uses the fake module for self.arxiv and that sort matches the fake SortCriterion
        searcher.arxiv = fake_arxiv
        searcher.sort = fake_arxiv.SortCriterion.Relevance

        # Execute the method under test
        results = searcher.search(max_results=1)

        # Assertions on returned structure
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Test Paper")
        self.assertEqual(results[0]["href"], "http://example.com/paper.pdf")
        self.assertEqual(results[0]["body"], "This is a summary.")

        # Verify the interactions with the fake arxiv objects
        fake_arxiv.Search.assert_called_once_with(query="quantum", max_results=1, sort_by=fake_arxiv.SortCriterion.Relevance)
        fake_arxiv.Client.assert_called_once()
        fake_client.results.assert_called_once()
