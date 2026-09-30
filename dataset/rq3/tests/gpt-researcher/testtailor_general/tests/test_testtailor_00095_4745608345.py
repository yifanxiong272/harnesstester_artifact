import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.context.retriever')
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
        """Verify _get_relevant_documents builds Document objects from pages."""
        retriever = SearchAPIRetriever()
        retriever.pages = [
            {"raw_content": "hello world", "title": "t1", "url": "u1"},
            {"title": "t2"},  # missing raw_content and url should use defaults
        ]

        docs = retriever._get_relevant_documents("some query", run_manager=None)

        self.assertIsInstance(docs, list)
        self.assertEqual(len(docs), 2)

        first, second = docs

        # first page values preserved
        self.assertEqual(first.page_content, "hello world")
        self.assertEqual(first.metadata, {"title": "t1", "source": "u1"})

        # second page missing raw_content and url -> defaults applied
        self.assertEqual(second.page_content, "")
        self.assertEqual(second.metadata, {"title": "t2", "source": ""})
