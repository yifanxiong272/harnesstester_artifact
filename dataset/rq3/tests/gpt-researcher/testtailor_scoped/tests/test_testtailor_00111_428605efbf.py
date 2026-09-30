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
        """Test that async_get_context calls the vector store async search with the provided
        query, k (max_results) and filter, and then passes the results to prompt_family.pretty_print_docs.
        """
        calls = {}

        class DummyVectorStore:
            async def asimilarity_search(self, query, k, filter):
                # record the call arguments
                calls['query'] = query
                calls['k'] = k
                calls['filter'] = filter
                # return a sample list of documents
                return [{'id': 'd1', 'content': 'alpha'}, {'id': 'd2', 'content': 'beta'}]

        class DummyPromptFamily:
            def pretty_print_docs(self, results):
                # record received results and return a formatted string
                calls['results'] = results
                return " | ".join(doc['content'] for doc in results)

        vector_store = DummyVectorStore()
        prompt_family = DummyPromptFamily()
        compressor = VectorstoreCompressor(
            vector_store=vector_store,
            max_results=10,               # different from method arg to ensure method arg is used
            filter={'category': 'test'},
            prompt_family=prompt_family,
        )

        # Run the async method and get the result
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(compressor.async_get_context("search query", max_results=3))

        # Assertions: return value, forwarded args, and results passed to pretty_print_docs
        self.assertEqual(result, "alpha | beta")
        self.assertEqual(calls['query'], "search query")
        self.assertEqual(calls['k'], 3)
        self.assertEqual(calls['filter'], {'category': 'test'})
        self.assertEqual(calls['results'], [{'id': 'd1', 'content': 'alpha'}, {'id': 'd2', 'content': 'beta'}])
