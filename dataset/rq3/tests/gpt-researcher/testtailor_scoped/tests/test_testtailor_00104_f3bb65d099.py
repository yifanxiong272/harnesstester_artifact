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
        """Test non-MCP retriever path where researcher should not be passed to retriever."""
        class DummyRetriever:
            # class name does not contain 'mcpretriever' so the non-MCP branch is taken
            def __init__(self, query, query_domains=None):
                self.query = query
                self.query_domains = query_domains

            def search(self):
                # return a predictable result to assert against
                return [{"query": self.query, "domains": self.query_domains}]

        query = "find this"
        domains = ["example.com", "test.com"]

        # Use __import__ to avoid adding an import statement at top-level
        asyncio = __import__('asyncio')
        # Call the async function and get results
        result = asyncio.run(get_search_results(query, DummyRetriever, query_domains=domains, researcher="ignored"))

        # Verify the retriever was constructed without a researcher and returned expected output
        self.assertEqual(result, [{"query": query, "domains": domains}])
