import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.skills.researcher')
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
        """Ensure MCP retriever presence logs the MCP-configured message"""
        # Create a dummy MCP retriever class whose __name__ contains "mcpretriever" when lowercased
        class McpRetriever:
            pass

        # Build a minimal researcher object with required attributes
        class Dummy:
            pass

        researcher = Dummy()
        researcher.query = "test query"
        researcher.retrievers = [McpRetriever]
        researcher.visited_urls = set()
        researcher.verbose = False
        researcher.agent = "agent_x"
        researcher.role = "role_x"
        researcher.source_urls = None
        researcher.complement_source_urls = False
        researcher.query_domains = None
        # Ensure report_source exists to avoid attribute errors
        researcher.report_source = None
        researcher.cfg = unittest.mock.MagicMock(curate_sources=False, max_search_results_per_query=3)
        researcher.vector_store = None
        researcher.parent_query = None
        researcher.headers = None
        researcher.prompt_family = unittest.mock.MagicMock(join_local_web_documents=lambda a, b: a + b)
        researcher.websocket = None
        researcher.get_costs = lambda: 0
        researcher.add_costs = lambda *a, **k: None
        researcher.context_manager = unittest.mock.MagicMock()
        researcher.scraper_manager = unittest.mock.MagicMock()
        researcher.documents = None
        researcher.document_urls = None
        researcher.vector_store_filter = None
        researcher.source_curator = unittest.mock.MagicMock()
        researcher.report_type = "main_report"
        researcher.kwargs = {}

        # Instantiate the conductor and override logger/json_handler to control side effects
        conductor = ResearchConductor(researcher)
        conductor.logger = unittest.mock.MagicMock()
        conductor.json_handler = None

        # Patch the web-search method to avoid executing complex internals (safe even if not called)
        with unittest.mock.patch.object(ResearchConductor, "_get_context_by_web_search", new=unittest.mock.AsyncMock(return_value=[])):
            # Run the async method
            asyncio.run(conductor.conduct_research())

        # Assert the specific log message for MCP retrievers was emitted
        conductor.logger.info.assert_any_call("MCP retrievers configured and will be used with standard research flow")
