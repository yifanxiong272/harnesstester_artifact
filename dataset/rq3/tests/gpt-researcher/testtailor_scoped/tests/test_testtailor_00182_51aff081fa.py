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
        """Ensure stream_output is awaited when researcher.verbose is True and VectorstoreCompressor is used."""
        # Acquire module where ContextManager is defined
        module = __import__(ContextManager.__module__, fromlist=["*"])

        # Backup original attributes to restore later
        orig_stream_output = getattr(module, "stream_output", None)
        orig_VectorstoreCompressor = getattr(module, "VectorstoreCompressor", None)

        # Prepare a place to record calls
        called = {}

        # Fake async stream_output to verify it is awaited and called with expected args
        async def fake_stream_output(*args, **kwargs):
            called["stream_args"] = args
            called["stream_kwargs"] = kwargs
            return None

        # Fake VectorstoreCompressor to avoid external dependencies
        class FakeVectorstoreCompressor:
            def __init__(self, vector_store, filter=None, prompt_family=None, **kwargs):
                self.vector_store = vector_store
                self.filter = filter
                self.prompt_family = prompt_family
                self.kwargs = kwargs
                called["compressor_init"] = {
                    "vector_store": vector_store,
                    "filter": filter,
                    "prompt_family": prompt_family,
                    "kwargs": kwargs,
                }

            async def async_get_context(self, query, max_results=8):
                # record call and return deterministic result
                called["async_get_context"] = {"query": query, "max_results": max_results}
                return f"COMPRESSED:{query}:{max_results}"

        # Patch module-level names
        module.stream_output = fake_stream_output
        module.VectorstoreCompressor = FakeVectorstoreCompressor

        try:
            # Create a simple researcher with verbose True to trigger the stream_output path
            class DummyResearcher:
                def __init__(self):
                    self.verbose = True
                    self.websocket = "fake_ws"
                    self.prompt_family = "pf"
                    self.kwargs = {}
                    self.vector_store = "fake_vector_store"

            researcher = DummyResearcher()
            cm = ContextManager(researcher)

            # Run the coroutine
            asyncio = __import__("asyncio")
            try:
                result = asyncio.get_event_loop().run_until_complete(
                    cm.get_similar_content_by_query_with_vectorstore("my query", {"tag": "x"})
                )
            except RuntimeError:
                # If event loop is already running, create a new one
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(
                        cm.get_similar_content_by_query_with_vectorstore("my query", {"tag": "x"})
                    )
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)

            # Assertions: ensure stream_output was called and the vectorstore compressor was used
            self.assertIn("stream_args", called, "stream_output was not called")
            args = called["stream_args"]
            # check the first two positional args and that the message contains the query
            self.assertEqual(args[0], "logs")
            self.assertEqual(args[1], "fetching_query_format")
            self.assertIn("my query", args[2])

            # Ensure compressor was constructed with the provided vector store and filter
            self.assertIn("compressor_init", called)
            self.assertEqual(called["compressor_init"]["vector_store"], "fake_vector_store")
            self.assertEqual(called["compressor_init"]["filter"], {"tag": "x"})

            # Ensure async_get_context was called and returned the expected value
            self.assertIn("async_get_context", called)
            self.assertEqual(called["async_get_context"]["query"], "my query")
            self.assertEqual(result, "COMPRESSED:my query:8")
        finally:
            # Restore originals
            if orig_stream_output is not None:
                module.stream_output = orig_stream_output
            else:
                delattr(module, "stream_output")
            if orig_VectorstoreCompressor is not None:
                module.VectorstoreCompressor = orig_VectorstoreCompressor
            else:
                delattr(module, "VectorstoreCompressor")
