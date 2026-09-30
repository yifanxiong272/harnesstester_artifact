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
        """Test that MCP retriever receives the researcher argument and its search() is used."""
        class MCPRetrieverFake:
            def __init__(self, query, query_domains=None, researcher=None):
                self.query = query
                self.query_domains = query_domains
                self.researcher = researcher

            def search(self):
                return [{
                    "query": self.query,
                    "domains": self.query_domains,
                    "researcher": self.researcher
                }]

        query = "find this"
        domains = ["example.com"]
        researcher = {"id": 123, "role": "researcher"}

        aio = __import__('asyncio')
        try:
            # Prefer asyncio.run when available
            if hasattr(aio, "run"):
                result = aio.run(get_search_results(query, MCPRetrieverFake, query_domains=domains, researcher=researcher))
            else:
                result = aio.get_event_loop().run_until_complete(get_search_results(query, MCPRetrieverFake, query_domains=domains, researcher=researcher))
        except RuntimeError:
            # If there's already a running loop, create a new one for the test
            loop = aio.new_event_loop()
            try:
                result = loop.run_until_complete(get_search_results(query, MCPRetrieverFake, query_domains=domains, researcher=researcher))
            finally:
                loop.close()

        self.assertIsInstance(result, list)
        self.assertEqual(result, [{
            "query": query,
            "domains": domains,
            "researcher": researcher
        }])
