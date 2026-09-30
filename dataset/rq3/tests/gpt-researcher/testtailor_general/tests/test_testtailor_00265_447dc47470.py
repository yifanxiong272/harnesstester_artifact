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
        """Ensure stream_output is awaited when researcher.verbose is True."""
        # Setup a fake researcher with the required attributes
        researcher = MagicMock()
        researcher.verbose = True
        researcher.websocket = "ws"
        researcher.prompt_family = "pf"
        researcher.kwargs = {}
        researcher.vector_store = "vs"
        researcher.memory = MagicMock()
        researcher.memory.get_embeddings.return_value = "embs"
        researcher.add_costs = MagicMock()

        cm = ContextManager(researcher)

        query = "find me relevant"
        filter_dict = {"tag": "important"}

        # Patch stream_output and VectorstoreCompressor in the module where ContextManager is defined
        module_path = ContextManager.__module__
        with patch(f"{module_path}.stream_output", new_callable=AsyncMock) as mock_stream_output, \
             patch(f"{module_path}.VectorstoreCompressor") as mock_vsc:

            # Configure the VectorstoreCompressor mock to return an object with async_get_context
            mock_instance = MagicMock()
            mock_instance.async_get_context = AsyncMock(return_value="compressed-context")
            mock_vsc.return_value = mock_instance

            # Call the method under test
            result = asyncio.run(cm.get_similar_content_by_query_with_vectorstore(query, filter_dict))

            # Assertions
            self.assertEqual(result, "compressed-context")
            mock_stream_output.assert_called_once_with(
                "logs",
                "fetching_query_format",
                f" Getting relevant content based on query: {query}...",
                researcher.websocket,
            )
