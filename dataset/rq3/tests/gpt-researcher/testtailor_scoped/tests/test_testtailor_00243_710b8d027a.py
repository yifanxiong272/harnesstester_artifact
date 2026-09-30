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
        """Ensure choose_agent is awaited and its return values set on the researcher when agent/role missing."""
        # Minimal cfg object
        class DummyCfg:
            def __init__(self):
                self.curate_sources = False
                self.max_search_results_per_query = 5
                self.mcp_strategy = None

        # Minimal researcher object using a simple class to avoid imports
        class DummyResearcher:
            def __init__(self):
                self.query = "test query"
                self.cfg = DummyCfg()
                self.parent_query = None
                self.add_costs = lambda *a, **k: None
                self.headers = None
                self.prompt_family = None
                # agent and role intentionally not set to trigger choose_agent path
                self.agent = None
                self.role = None
                self.retrievers = []  # no retrievers to keep flow simple
                self.visited_urls = set()
                self.verbose = False  # avoid stream_output side-effects
                self.websocket = None
                self.source_urls = ["http://example.com"]  # make conduct_research choose the URL branch
                self.complement_source_urls = False
                self.query_domains = []
                self.vector_store = None
                self.report_source = None
                self.documents = None
                self.document_urls = None
                self.report_type = None
                # used by some methods but not in this test path
                self.scraper_manager = None
                self.context_manager = None
                self.source_curator = None

        researcher = DummyResearcher()

        # Instantiate the conductor
        conductor = ResearchConductor(researcher)
        # Avoid interacting with any actual json handler
        conductor.json_handler = None

        # Prepare a fake choose_agent coroutine and track invocation
        called = {"count": 0}
        async def fake_choose_agent(query, cfg, parent_query, cost_callback, headers, prompt_family):
            called["count"] += 1
            # return a tuple (agent, role)
            return ("chosen_agent", "chosen_role")

        # Replace the choose_agent global used by the conduct_research function
        original_choose = ResearchConductor.conduct_research.__globals__.get("choose_agent")
        ResearchConductor.conduct_research.__globals__["choose_agent"] = fake_choose_agent

        # Stub out _get_context_by_urls to avoid external scraping calls; return a simple context
        async def fake_get_context_by_urls(urls):
            return "stubbed context from urls"

        conductor._get_context_by_urls = fake_get_context_by_urls

        # Run the async conduct_research and assert behavior
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(conductor.conduct_research())

            # choose_agent should have been called exactly once
            self.assertEqual(called["count"], 1, "choose_agent was not called exactly once")

            # The researcher.agent and researcher.role should be set from fake_choose_agent
            self.assertEqual(researcher.agent, "chosen_agent")
            self.assertEqual(researcher.role, "chosen_role")

            # The returned context should be what our fake_get_context_by_urls provided
            self.assertEqual(result, "stubbed context from urls")
        finally:
            # Restore the original choose_agent to avoid affecting other tests
            if original_choose is not None:
                ResearchConductor.conduct_research.__globals__["choose_agent"] = original_choose
            else:
                ResearchConductor.conduct_research.__globals__.pop("choose_agent", None)
            try:
                loop.close()
            except Exception:
                pass
