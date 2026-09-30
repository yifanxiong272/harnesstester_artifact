import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.actions.query_processing')
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
        """Ensure non-MCP retriever path constructs retriever without researcher and calls search."""
        # Define a simple retriever class whose __name__ does not contain 'mcpretriever'
        class SimpleRetriever:
            def __init__(self, query, query_domains=None):
                # record values to return via search
                self.query = query
                self.query_domains = query_domains

            def search(self):
                # return a predictable result that encodes what was passed in
                return [{"title": "result", "query": self.query, "domains": self.query_domains}]

        # Sanity check: ensure we will hit the non-MCP branch
        self.assertFalse("mcpretriever" in SimpleRetriever.__name__.lower())

        query = "unit test query"
        domains = ["example.com"]
        # Pass a researcher object; it should NOT be forwarded to SimpleRetriever
        fake_researcher = object()

        # Call the async function: get the coroutine and drive its __await__ to completion
        coro = get_search_results(query, SimpleRetriever, query_domains=domains, researcher=fake_researcher)
        iterator = coro.__await__()
        try:
            while True:
                next(iterator)
        except StopIteration as e:
            results = e.value

        # Verify the returned results and that the retriever received the expected args
        expected = [{"title": "result", "query": query, "domains": domains}]
        self.assertEqual(results, expected)
