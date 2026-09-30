import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.context.compression')
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
        """Ensure __get_contextual_retriever builds the pipeline with expected components."""
        # Access module where ContextCompressor is defined using built-in __import__
        mod = __import__(ContextCompressor.__module__, fromlist=['*'])

        # Backup any existing attributes to restore later
        backup = {}
        names = [
            "RecursiveCharacterTextSplitter",
            "EmbeddingsFilter",
            "DocumentCompressorPipeline",
            "SearchAPIRetriever",
            "ContextualCompressionRetriever",
        ]
        for n in names:
            backup[n] = getattr(mod, n, None)

        # Define simple dummy classes to observe construction
        class DummySplitter:
            def __init__(self, chunk_size=0, chunk_overlap=0):
                self.chunk_size = chunk_size
                self.chunk_overlap = chunk_overlap

        class DummyFilter:
            def __init__(self, embeddings=None, similarity_threshold=None):
                self.embeddings = embeddings
                self.similarity_threshold = similarity_threshold

        class DummyPipeline:
            def __init__(self, transformers=None):
                self.transformers = list(transformers or [])

        class DummyRetriever:
            def __init__(self, pages=None):
                self.pages = pages

        class DummyContextual:
            def __init__(self, base_compressor=None, base_retriever=None):
                self.base_compressor = base_compressor
                self.base_retriever = base_retriever

        # Inject our dummies into the module namespace so the method under test uses them
        try:
            mod.RecursiveCharacterTextSplitter = DummySplitter
            mod.EmbeddingsFilter = DummyFilter
            mod.DocumentCompressorPipeline = DummyPipeline
            mod.SearchAPIRetriever = DummyRetriever
            mod.ContextualCompressionRetriever = DummyContextual

            # Create a ContextCompressor with minimal inputs
            docs = [{"raw_content": "some content"}, {"raw_content": "more content"}]
            compressor = ContextCompressor(documents=docs, embeddings="fake-emb")

            # Call the (name-mangled) private method to build the pipeline
            retriever = compressor._ContextCompressor__get_contextual_retriever()

            # Assert we got our DummyContextual back and its parts wired correctly
            self.assertIsInstance(retriever, DummyContextual)
            self.assertIsInstance(retriever.base_compressor, DummyPipeline)
            self.assertIsInstance(retriever.base_retriever, DummyRetriever)

            # Pipeline should contain a splitter and a filter in order
            transformers = retriever.base_compressor.transformers
            self.assertGreaterEqual(len(transformers), 2)
            splitter_instance, filter_instance = transformers[0], transformers[1]
            self.assertIsInstance(splitter_instance, DummySplitter)
            self.assertIsInstance(filter_instance, DummyFilter)

            # Check that splitter was configured with expected defaults
            self.assertEqual(splitter_instance.chunk_size, 1000)
            self.assertEqual(splitter_instance.chunk_overlap, 100)

            # Check the retriever was given the original documents
            self.assertIs(retriever.base_retriever.pages, compressor.documents)
        finally:
            # Restore module attributes
            for n, val in backup.items():
                if val is None:
                    if hasattr(mod, n):
                        delattr(mod, n)
                else:
                    setattr(mod, n, val)
