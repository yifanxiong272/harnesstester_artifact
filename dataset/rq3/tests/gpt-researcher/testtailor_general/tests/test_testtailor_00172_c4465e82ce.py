import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.skills.context_manager')
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
        """complete the test case here"""
        # Arrange: create a fake ContextCompressor to capture initialization and call args
        class FakeContextCompressor:
            last_instance = None

            def __init__(self, documents, embeddings, prompt_family, **kwargs):
                # store values for assertions
                self.documents = documents
                self.embeddings = embeddings
                self.prompt_family = prompt_family
                self.kwargs = kwargs
                FakeContextCompressor.last_instance = self

            async def async_get_context(self, query, max_results=10, cost_callback=None):
                # record call parameters and return a predictable value
                self.called_query = query
                self.called_max_results = max_results
                self.called_cost_callback = cost_callback
                return "COMPRESSED-CONTEXT"

        # Patch the ContextCompressor in the module where ContextManager is defined
        module_name = ContextManager.__module__
        module = __import__(module_name, fromlist=["*"])
        original_context_compressor = getattr(module, "ContextCompressor", None)
        setattr(module, "ContextCompressor", FakeContextCompressor)

        # Create a minimal fake researcher with required attributes
        class DummyMemory:
            def get_embeddings(self):
                return "DUMMY-EMBEDDINGS"

        class DummyResearcher:
            def __init__(self):
                self.verbose = False
                self.memory = DummyMemory()
                self.prompt_family = "dummy-family"
                self.kwargs = {"extra": "value"}
                self.websocket = None

            def add_costs(self, *args, **kwargs):
                # simple placeholder
                return None

        researcher = DummyResearcher()
        context_manager = ContextManager(researcher)

        query = "test query"
        pages = ["page1 content", "page2 content"]

        # Act: call the async method synchronously using an event loop
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                context_manager.get_similar_content_by_query(query=query, pages=pages)
            )
        finally:
            asyncio.set_event_loop(None)
            loop.close()
            # Restore original ContextCompressor in module
            if original_context_compressor is None:
                delattr(module, "ContextCompressor")
            else:
                setattr(module, "ContextCompressor", original_context_compressor)

        # Assert: returned value and that FakeContextCompressor received expected inputs
        self.assertEqual(result, "COMPRESSED-CONTEXT")
        inst = FakeContextCompressor.last_instance
        self.assertIsNotNone(inst, "ContextCompressor was not instantiated")
        self.assertEqual(inst.documents, pages)
        self.assertEqual(inst.embeddings, "DUMMY-EMBEDDINGS")
        self.assertEqual(inst.prompt_family, "dummy-family")
        self.assertEqual(inst.called_query, query)
        self.assertEqual(inst.called_max_results, 10)
        self.assertEqual(inst.called_cost_callback, researcher.add_costs)
