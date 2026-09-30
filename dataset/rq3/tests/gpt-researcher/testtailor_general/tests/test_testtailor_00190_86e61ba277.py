import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.scraper.browser.processing.scrape_skills')
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
        expected_text = "fake pdf content from arxiv"

        class FakeDoc:
            def __init__(self, content):
                self.page_content = content

        class FakeArxivRetriever:
            last_kwargs = None
            last_query = None

            def __init__(self, load_max_docs, doc_content_chars_max):
                FakeArxivRetriever.last_kwargs = {
                    "load_max_docs": load_max_docs,
                    "doc_content_chars_max": doc_content_chars_max,
                }

            def get_relevant_documents(self, query):
                FakeArxivRetriever.last_query = query
                return [FakeDoc(expected_text)]

        # Monkeypatch the ArxivRetriever used by the function under test
        original = scrape_pdf_with_arxiv.__globals__.get("ArxivRetriever", None)
        try:
            scrape_pdf_with_arxiv.__globals__["ArxivRetriever"] = FakeArxivRetriever
            result = scrape_pdf_with_arxiv("test query")
            self.assertEqual(result, expected_text)
            # Verify the constructor was called with the expected defaults
            self.assertEqual(
                FakeArxivRetriever.last_kwargs,
                {"load_max_docs": 2, "doc_content_chars_max": None},
            )
            # Verify the query was forwarded
            self.assertEqual(FakeArxivRetriever.last_query, "test query")
        finally:
            # Restore original ArxivRetriever to avoid side effects
            if original is None:
                del scrape_pdf_with_arxiv.__globals__["ArxivRetriever"]
            else:
                scrape_pdf_with_arxiv.__globals__["ArxivRetriever"] = original
