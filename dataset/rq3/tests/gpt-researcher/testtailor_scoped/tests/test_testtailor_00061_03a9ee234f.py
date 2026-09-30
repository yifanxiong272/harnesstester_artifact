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
        """Ensure stream_output is called when researcher.verbose is True and ContextCompressor is used."""
        # Fake researcher and dependencies
        class FakeMemory:
            def get_embeddings(self):
                return "fake-embeddings"

        class FakeResearcher:
            def __init__(self):
                self.verbose = True
                self.websocket = "fake-websocket"
                self.memory = FakeMemory()
                self.prompt_family = "fake-prompt-family"
                self.kwargs = {"fake_kw": True}
                self.add_costs = lambda *args, **kwargs: None

        researcher = FakeResearcher()
        context_manager = ContextManager(researcher)

        # Capture calls to stream_output
        calls = []

        async def fake_stream_output(channel, event, message, websocket):
            calls.append((channel, event, message, websocket))
            return None

        # Fake ContextCompressor used by the method
        class FakeContextCompressor:
            def __init__(self, documents, embeddings, prompt_family, **kwargs):
                # basic sanity checks to ensure constructor is called with expected args
                self.documents = documents
                self.embeddings = embeddings
                self.prompt_family = prompt_family
                self.kwargs = kwargs

            async def async_get_context(self, query, max_results, cost_callback=None):
                # ensure the method receives expected parameters
                assert query == "test query"
                assert max_results == 10
                assert callable(cost_callback)
                return "COMPRESSED_RESULT"

        # Patch the globals used inside the target method to use our fakes
        gm = ContextManager.get_similar_content_by_query.__globals__
        original_stream = gm.get("stream_output")
        original_compressor = gm.get("ContextCompressor")
        gm["stream_output"] = fake_stream_output
        gm["ContextCompressor"] = FakeContextCompressor

        try:
            # Run the async method and verify results
            result = asyncio.get_event_loop().run_until_complete(
                context_manager.get_similar_content_by_query("test query", ["page A", "page B"])
            )
            self.assertEqual(result, "COMPRESSED_RESULT")

            # Verify stream_output was called once with expected pieces
            self.assertEqual(len(calls), 1)
            channel, event, message, websocket = calls[0]
            self.assertEqual(channel, "logs")
            self.assertEqual(event, "fetching_query_content")
            self.assertIn("test query", message)
            self.assertEqual(websocket, researcher.websocket)
        finally:
            # restore originals to avoid side effects on other tests
            if original_stream is not None:
                gm["stream_output"] = original_stream
            else:
                gm.pop("stream_output", None)
            if original_compressor is not None:
                gm["ContextCompressor"] = original_compressor
            else:
                gm.pop("ContextCompressor", None)
