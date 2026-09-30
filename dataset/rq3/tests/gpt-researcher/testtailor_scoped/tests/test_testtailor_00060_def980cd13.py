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

        d1 = DummyDoc("content1", {"title": "t1"})
        d2 = DummyDoc("content2", {"title": "t2"})
        documents = [d1, d2]

        loader = LangChainDocumentLoader(documents)

        # ensure the documents attribute was set to the provided list (identity)
        self.assertIs(loader.documents, documents)
        # sanity checks on contents
        self.assertEqual(len(loader.documents), 2)
        self.assertIs(loader.documents[0], d1)
        self.assertEqual(loader.documents[1].page_content, "content2")
