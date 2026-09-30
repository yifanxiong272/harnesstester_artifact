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
        """Test ResearchConductor.plan_research calls search and planning helpers and returns outline."""
        # Prepare a minimal fake researcher object
        class FakeRetriever:
            pass

        class FakeCfg:
            max_search_results_per_query = 5
            mcp_strategy = None
            # other cfg attributes may be present but not used here

        class FakeResearcher:
            def __init__(self):
                self.websocket = "fake_ws"
                self.retrievers = [FakeRetriever]
                self.role = "tester_role_prompt"
                self.cfg = FakeCfg()
                self.parent_query = None
                self.report_type = "main_report"
                self.add_costs = lambda *a, **k: None
                self.kwargs = {}
                self.verbose = False
                self.visited_urls = set()
                self.scraper_manager = None
                self.context_manager = None
                self.retriever = None

        researcher = FakeResearcher()
        conductor = ResearchConductor(researcher)

        # Capture calls to the fake functions
        get_search_calls = []
        outline_calls = []
        stream_calls = []

        # Define fake async replacements and inject them into the plan_research globals
        async def fake_stream_output(*args, **kwargs):
            stream_calls.append(args)
            return None

        async def fake_get_search_results(query, retriever, query_domains, researcher=None):
            get_search_calls.append({
                "query": query,
                "retriever": retriever,
                "query_domains": query_domains,
                "researcher": researcher
            })
            # return a list of dummy search results
            return [{"href": "http://example.com", "body": "example snippet"}]

        async def fake_plan_research_outline(*args, **kwargs):
            outline_calls.append({"args": args, "kwargs": kwargs})
            return ["subquery1", "subquery2"]

        # Inject fakes into the function globals so the method uses them
        pr_globals = ResearchConductor.plan_research.__globals__
        orig_stream = pr_globals.get("stream_output")
        orig_search = pr_globals.get("get_search_results")
        orig_outline = pr_globals.get("plan_research_outline")

        pr_globals["stream_output"] = fake_stream_output
        pr_globals["get_search_results"] = fake_get_search_results
        pr_globals["plan_research_outline"] = fake_plan_research_outline

        try:
            # Run the coroutine
            result = asyncio.get_event_loop().run_until_complete(conductor.plan_research("my query", None))

            # Assertions: ensure the fake helpers were invoked and the outline returned
            self.assertEqual(result, ["subquery1", "subquery2"])
            self.assertEqual(len(get_search_calls), 1)
            self.assertEqual(get_search_calls[0]["query"], "my query")
            # retriever passed should be the first retriever configured on the researcher
            self.assertIs(get_search_calls[0]["retriever"], researcher.retrievers[0])
            # plan_research_outline should have been called once
            self.assertEqual(len(outline_calls), 1)
            # stream_output should have been called at least twice (start browsing + planning)
            self.assertTrue(len(stream_calls) >= 2)
        finally:
            # Restore originals
            if orig_stream is not None:
                pr_globals["stream_output"] = orig_stream
            else:
                pr_globals.pop("stream_output", None)

            if orig_search is not None:
                pr_globals["get_search_results"] = orig_search
            else:
                pr_globals.pop("get_search_results", None)

            if orig_outline is not None:
                pr_globals["plan_research_outline"] = orig_outline
            else:
                pr_globals.pop("plan_research_outline", None)
