import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.document.langchain_document')
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
        """Verify load collects page_content and metadata 'title' into dicts."""
        # Simple stand-in for a LangChain Document-like object
        class DummyDoc:
            def __init__(self, page_content, metadata):
                self.page_content = page_content
                self.metadata = metadata

        docs = [
            DummyDoc("first content", {"title": "https://example.com/1"}),
            DummyDoc("second content", {"title": "https://example.com/2"}),
        ]

        loader = LangChainDocumentLoader(docs)
        # run the async load method
        result = asyncio.run(loader.load())

        expected = [
            {"raw_content": "first content", "url": "https://example.com/1"},
            {"raw_content": "second content", "url": "https://example.com/2"},
        ]

        self.assertEqual(result, expected)
