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
        """Ensure the constructor stores the documents list as-is."""
        class DummyDocument:
            def __init__(self, content, metadata=None):
                self.page_content = content
                self.metadata = metadata or {}

        docs = [DummyDocument("first"), DummyDocument("second")]
        loader = LangChainDocumentLoader(docs)

        # The loader should keep the same list reference
        self.assertIs(loader.documents, docs)
        # And the contents should be preserved
        self.assertEqual([d.page_content for d in loader.documents], ["first", "second"])
