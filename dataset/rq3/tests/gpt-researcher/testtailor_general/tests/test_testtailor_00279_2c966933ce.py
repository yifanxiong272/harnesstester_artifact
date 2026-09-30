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
        """Ensure GPT-Researcher documents are converted to Langchain Document objects"""
        # Create the wrapper with a dummy vector store (not used by the method under test)
        wrapper = VectorStoreWrapper(vector_store=None)

        # Input data mimicking GPT Researcher Document format
        data = [
            {"raw_content": "Hello world", "url": "http://example.com/a"},
            {"raw_content": "Second document content", "url": "http://example.com/b"},
        ]

        # Invoke the target method
        result = wrapper._create_langchain_documents(data)

        # Assertions: correct number of documents and proper mapping of fields
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

        first, second = result

        # Each result should be a Document with page_content and metadata.source set
        self.assertEqual(first.page_content, "Hello world")
        self.assertIsInstance(first.metadata, dict)
        self.assertEqual(first.metadata.get("source"), "http://example.com/a")

        self.assertEqual(second.page_content, "Second document content")
        self.assertIsInstance(second.metadata, dict)
        self.assertEqual(second.metadata.get("source"), "http://example.com/b")
