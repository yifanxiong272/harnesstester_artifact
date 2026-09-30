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
        """Test ResearchConductor.plan_research calls search and planning utilities and returns outline."""
        # Load the module where ResearchConductor is defined
        rc_module = __import__(ResearchConductor.__module__, fromlist=['*'])

        # Save originals to restore later
        orig_get_search = getattr(rc_module, "get_search_results", None)
        orig_plan_outline = getattr(rc_module, "plan_research_outline", None)
        orig_stream_output = getattr(rc_module, "stream_output", None)

        calls = {}

        async def fake_stream_output(channel, event, message, websocket, *a, **k):
            # record minimal info about calls
            calls.setdefault("stream_calls", []).append((channel, event, message))

        async def fake_get_search_results(query, retriever, query_domains, researcher=None):
            calls["get_search_called"] = {
                "query": query,
                "retriever": retriever,
                "query_domains": query_domains,
                "researcher": researcher,
            }
            # Return a small list to simulate search results
            return [{"href": "http://example.com", "title": "Example", "body": "Example content"}]

        async def fake_plan_research_outline(**kwargs):
            # Capture kwargs passed to plan_research_outline and return a sample outline
            calls["plan_outline_kwargs"] = kwargs
            return ["subquery-1", "subquery-2"]

        # Inject fakes
        setattr(rc_module, "stream_output", fake_stream_output)
        setattr(rc_module, "get_search_results", fake_get_search_results)
        setattr(rc_module, "plan_research_outline", fake_plan_research_outline)

        try:
            # Build a minimal researcher with required attributes using a simple dynamic class
            researcher = type("R", (), {})()
            researcher.websocket = None

            # Dummy retriever class to provide __name__
            class DummyRetriever:
                pass

            researcher.retrievers = [DummyRetriever]
            researcher.role = "test-role"
            researcher.cfg = type("C", (), {})()
            researcher.cfg.max_search_results_per_query = 5
            researcher.parent_query = None
            researcher.report_type = "main_report"
            researcher.add_costs = lambda *a, **k: None
            researcher.kwargs = {}
            researcher.headers = None
            researcher.query_domains = None
            researcher.verbose = False
            researcher.visited_urls = set()

            conductor = ResearchConductor(researcher)

            # Run the coroutine under test
            outline = asyncio.run(conductor.plan_research("find test info", query_domains=["example.com"]))

            # Assertions: the returned outline should match our fake_plan_research_outline result
            self.assertEqual(outline, ["subquery-1", "subquery-2"])

            # Ensure get_search_results was called with expected query and retriever
            self.assertIn("get_search_called", calls)
            self.assertEqual(calls["get_search_called"]["query"], "find test info")
            # The retriever passed should be the first class in researcher.retrievers
            self.assertIs(calls["get_search_called"]["retriever"], DummyRetriever)

            # Ensure plan_research_outline received expected keyword args including retriever_names
            self.assertIn("plan_outline_kwargs", calls)
            kwargs = calls["plan_outline_kwargs"]
            self.assertEqual(kwargs["query"], "find test info")
            # retriever_names should be a list with DummyRetriever.__name__
            self.assertEqual(kwargs["retriever_names"], [DummyRetriever.__name__])

            # Check that stream_output was called at least twice (for the two log messages)
            self.assertIn("stream_calls", calls)
            self.assertGreaterEqual(len(calls["stream_calls"]), 2)

        finally:
            # Restore original functions
            if orig_get_search is not None:
                setattr(rc_module, "get_search_results", orig_get_search)
            else:
                if hasattr(rc_module, "get_search_results"):
                    delattr(rc_module, "get_search_results")

            if orig_plan_outline is not None:
                setattr(rc_module, "plan_research_outline", orig_plan_outline)
            else:
                if hasattr(rc_module, "plan_research_outline"):
                    delattr(rc_module, "plan_research_outline")

            if orig_stream_output is not None:
                setattr(rc_module, "stream_output", orig_stream_output)
            else:
                if hasattr(rc_module, "stream_output"):
                    delattr(rc_module, "stream_output")
