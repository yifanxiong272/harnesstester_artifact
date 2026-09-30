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
        class DummyDoc:
            def __init__(self, page_content, metadata):
                self.page_content = page_content
                self.metadata = metadata

        docs_in = [
            DummyDoc("content1", {"title": "http://example.com/1"}),
            DummyDoc("content2", {"other_key": "http://example.com/2"}),
        ]

        loader = LangChainDocumentLoader(docs_in)
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(loader.load())

        expected = [
            {"raw_content": "content1", "url": "http://example.com/1"},
            {"raw_content": "content2", "url": ""},
        ]

        self.assertEqual(result, expected)
