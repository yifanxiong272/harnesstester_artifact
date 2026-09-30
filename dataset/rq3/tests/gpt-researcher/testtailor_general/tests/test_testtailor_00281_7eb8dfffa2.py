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
        """Test that conduct_research emits the initial verbose stream outputs when verbose=True"""
        # Minimal dummy objects/classes to satisfy ResearchConductor expectations
        dummy_ws = object()

        class DummyRetriever:
            pass

        class DummyScraperManager:
            async def browse_urls(self, urls):
                return []

        class DummyContextManager:
            async def get_similar_content_by_query(self, query, scraped_content):
                return "sim"

            async def get_similar_content_by_query_with_vectorstore(self, query, filter):
                return "vec-sim"

        class DummyPromptFamily:
            def join_local_web_documents(self, a, b):
                return ""

        class DummySourceCurator:
            async def curate_sources(self, data):
                return data

        class Cfg:
            def __init__(self):
                self.curate_sources = False
                self.max_search_results_per_query = 1

        # Build a simple researcher object with required attributes
        researcher = type("R", (), {})()
        researcher.query = "test query"
        researcher.retrievers = [DummyRetriever]
        researcher.visited_urls = set()
        researcher.verbose = True
        researcher.websocket = dummy_ws
        researcher.agent = "predefined-agent"
        researcher.role = "predefined-role"
        researcher.source_urls = None
        researcher.complement_source_urls = False
        # Use Web report source so conduct_research will call _get_context_by_web_search
        researcher.report_source = ReportSource.Web.value
        researcher.query_domains = []
        researcher.cfg = Cfg()
        researcher.vector_store = None
        researcher.prompt_family = DummyPromptFamily()
        researcher.parent_query = None
        researcher.report_type = None
        researcher.documents = None
        researcher.vector_store_filter = None
        researcher.scraper_manager = DummyScraperManager()
        researcher.context_manager = DummyContextManager()
        researcher.add_costs = lambda *a, **k: None
        researcher.get_costs = lambda: 0
        researcher.source_curator = DummySourceCurator()
        researcher.add_research_sources = lambda *a, **k: None
        researcher.headers = {}
        researcher.query_domains = []

        conductor = ResearchConductor(researcher)

        # Stub out the web search to avoid complex internal behavior
        async def fake_get_context_by_web_search(query, scraped_data=None, query_domains=None):
            return "web context"

        conductor._get_context_by_web_search = fake_get_context_by_web_search

        # Patch stream_output in the module where ResearchConductor is defined to capture calls
        module_path = ResearchConductor.__module__
        with patch(f"{module_path}.stream_output", new_callable=AsyncMock) as mock_stream:
            # Run the async conduct_research
            result = asyncio.run(conductor.conduct_research())

            # Verify the function returned the stubbed context
            self.assertEqual(result, "web context")

            # Ensure stream_output was awaited at least twice (starting_research and agent_generated)
            self.assertGreaterEqual(len(mock_stream.await_args_list), 2)

            # Inspect the first two calls' positional arguments
            first_call = mock_stream.await_args_list[0]
            second_call = mock_stream.await_args_list[1]
            first_call_args, first_call_kwargs = first_call
            second_call_args, second_call_kwargs = second_call

            # Validate the first call corresponds to starting_research with the query and websocket
            self.assertEqual(first_call_args[0], "logs")
            self.assertEqual(first_call_args[1], "starting_research")
            self.assertIn(researcher.query, first_call_args[2])
            self.assertIs(first_call_args[3], dummy_ws)

            # Validate the second call corresponds to agent_generated with the researcher.agent and websocket
            self.assertEqual(second_call_args[0], "logs")
            self.assertEqual(second_call_args[1], "agent_generated")
            self.assertEqual(second_call_args[2], researcher.agent)
            self.assertIs(second_call_args[3], dummy_ws)
