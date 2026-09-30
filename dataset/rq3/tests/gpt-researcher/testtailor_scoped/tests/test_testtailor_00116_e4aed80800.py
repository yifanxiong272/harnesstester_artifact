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
        """Test that ArxivSearch.search calls the arxiv Client.results with the Search object
        and that it returns the expected transformed list of dicts."""
        # Prepare a mock arxiv module with the pieces ArxivSearch expects
        mock_arxiv = MagicMock()
        # Provide SortCriterion attributes used in __init__
        mock_arxiv.SortCriterion = type("SC", (), {"Relevance": "rel", "SubmittedDate": "date"})
        # Prepare a fake Search return value (the object passed into Client.results)
        search_obj = object()
        mock_arxiv.Search = MagicMock(return_value=search_obj)

        # Prepare a fake result object that the client.results will yield
        fake_result = MagicMock()
        fake_result.title = "Fake Title"
        fake_result.pdf_url = "http://example.com/fake.pdf"
        fake_result.summary = "Fake summary text."

        # Prepare client instance whose results() returns an iterable with our fake_result
        client_instance = MagicMock()
        client_instance.results.return_value = [fake_result]
        mock_arxiv.Client = MagicMock(return_value=client_instance)

        # Patch the module-level arxiv used by ArxivSearch to our mock_arxiv
        import sys
        mod = sys.modules[ArxivSearch.__module__]
        original_arxiv = getattr(mod, "arxiv", None)
        mod.arxiv = mock_arxiv

        try:
            # Instantiate ArxivSearch (will pick up mock_arxiv in __init__)
            arxiv_search = ArxivSearch(query="my test query", sort="Relevance")

            # Sanity: the instance should use our mock arxiv
            self.assertIs(arxiv_search.arxiv, mock_arxiv)

            # Call the method under test
            results = arxiv_search.search(max_results=1)

            # Validate returned structure and contents
            self.assertIsInstance(results, list)
            self.assertEqual(len(results), 1)
            item = results[0]
            self.assertEqual(item["title"], "Fake Title")
            self.assertEqual(item["href"], "http://example.com/fake.pdf")
            self.assertEqual(item["body"], "Fake summary text.")

            # Ensure the client.results was called with the object returned by Search
            client_instance.results.assert_called_once_with(search_obj)

            # Ensure Search was called with expected args, including sort_by set from SortCriterion.Relevance
            mock_arxiv.Search.assert_called_once_with(query="my test query", max_results=1, sort_by="rel")
        finally:
            # Restore original module-level arxiv to avoid side effects
            if original_arxiv is None:
                delattr(mod, "arxiv")
            else:
                mod.arxiv = original_arxiv
