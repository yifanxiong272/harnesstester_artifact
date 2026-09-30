import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.vector_store.vector_store')
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
        """Ensure load calls creation, splitting and forwards chunks to vector_store.add_documents"""
        # prepare a mock vector store
        mock_vs = unittest.mock.Mock()

        # create wrapper with the mock vector store
        wrapper = VectorStoreWrapper(mock_vs)

        # prepare input documents
        input_docs = [{"raw_content": "some long text", "url": "http://example"}]

        # replace internal methods to avoid langchain dependencies and to observe calls
        called = {"create": False, "split": False}

        def fake_create(docs):
            called["create"] = True
            # ensure the original documents are passed through
            self.assertEqual(docs, input_docs)
            # return a fake "langchain" document list
            return ["lang_doc"]

        def fake_split(docs):
            called["split"] = True
            # ensure the langchain documents are passed through
            self.assertEqual(docs, ["lang_doc"])
            # return fake splitted chunks
            return ["chunk_a", "chunk_b"]

        wrapper._create_langchain_documents = fake_create
        wrapper._split_documents = fake_split

        # execute the code under test
        wrapper.load(input_docs)

        # verify add_documents was invoked with the splitted chunks
        mock_vs.add_documents.assert_called_once_with(["chunk_a", "chunk_b"])

        # verify both internal steps were executed
        self.assertTrue(called["create"])
        self.assertTrue(called["split"])
