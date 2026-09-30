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
        """Ensure MCP retriever receives the researcher argument and is used in search()"""
        # Define a retriever whose class name includes 'MCPRetriever' so the branch is taken
        class MCPRetriever:
            def __init__(self, query, query_domains=None, researcher=None):
                self.query = query
                self.query_domains = query_domains
                self.researcher = researcher

            def search(self):
                # Return information that allows the test to verify the researcher was passed through
                return [
                    {
                        "query": self.query,
                        "domains": self.query_domains,
                        "researcher_name": getattr(self.researcher, "name", None),
                    }
                ]

        # Create a dummy researcher object
        class DummyResearcher:
            pass

        researcher = DummyResearcher()
        researcher.name = "test_researcher"

        # Use __import__ to obtain asyncio without a top-level import statement
        aio = __import__("asyncio")
        results = aio.run(
            get_search_results("test query", MCPRetriever, query_domains=["example.com"], researcher=researcher)
        )

        # Assert the search() result reflects the passed arguments, especially the researcher
        self.assertEqual(
            results,
            [
                {
                    "query": "test query",
                    "domains": ["example.com"],
                    "researcher_name": "test_researcher",
                }
            ],
        )
