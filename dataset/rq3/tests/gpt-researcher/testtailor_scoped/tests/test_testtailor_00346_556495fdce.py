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
        """Ensure stream_output is called when researcher.verbose is True and
        WrittenContentCompressor.async_get_context is awaited and its result returned.
        """
        # Prepare a simple researcher object with required attributes
        class DummyMemory:
            def get_embeddings(self_inner):
                return "dummy-embeddings"

        class DummyResearcher:
            def __init__(self):
                self.verbose = True
                self.websocket = "ws://dummy"
                self.memory = DummyMemory()
                self.kwargs = {"extra": "value"}
                # add_costs will be passed as a callback; a no-op is fine
                async def _add_costs(*args, **kwargs):
                    return None
                self.add_costs = _add_costs

        researcher = DummyResearcher()
        cm = ContextManager(researcher)

        # Access the underlying function object to patch its globals
        func = ContextManager.__dict__['_ContextManager__get_similar_written_contents_by_query']

        # Create AsyncMock for stream_output and patch into function globals
        stream_output_mock = AsyncMock()
        func.__globals__['stream_output'] = stream_output_mock

        # Create a mock WrittenContentCompressor class whose instance has async_get_context
        compressor_instance = Mock()
        compressor_instance.async_get_context = AsyncMock(return_value=["similar A", "similar B"])
        compressor_class_mock = Mock(return_value=compressor_instance)
        func.__globals__['WrittenContentCompressor'] = compressor_class_mock

        # Prepare inputs
        query = "test query"
        written_contents = [{"id": 1, "text": "abc"}, {"id": 2, "text": "def"}]
        similarity_threshold = 0.7
        max_results = 2

        # Call the private async method
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            cm._ContextManager__get_similar_written_contents_by_query(
                query, written_contents, similarity_threshold=similarity_threshold, max_results=max_results
            )
        )

        # Assertions
        # stream_output should have been awaited with expected args
        stream_output_mock.assert_awaited_once()
        called_args = stream_output_mock.await_args.args
        self.assertEqual(called_args[0], "logs")
        self.assertEqual(called_args[1], "fetching_relevant_written_content")
        self.assertIn(query, called_args[2])
        self.assertEqual(called_args[3], researcher.websocket)

        # WrittenContentCompressor should have been constructed with expected kwargs
        compressor_class_mock.assert_called_once()
        called_kwargs = compressor_class_mock.call_args.kwargs
        self.assertIs(called_kwargs.get("documents"), written_contents)
        self.assertEqual(called_kwargs.get("embeddings"), "dummy-embeddings")
        self.assertEqual(called_kwargs.get("similarity_threshold"), similarity_threshold)
        # ensure extra kwargs from researcher.kwargs were forwarded
        self.assertEqual(called_kwargs.get("extra"), "value")

        # The returned result should be what async_get_context returned
        self.assertEqual(result, ["similar A", "similar B"])
