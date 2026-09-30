import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('multi_agents.agents.researcher')
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
        """Test that ResearchAgent.research constructs a GPTResearcher, runs its methods, and returns the report."""
        # Prepare a place to capture created DummyResearcher instances
        created = []

        # Define a dummy GPTResearcher to replace the real one during the test
        class DummyResearcher:
            def __init__(self, query, report_type, parent_query, verbose, report_source, tone, websocket, headers):
                # store parameters for assertions
                self.query = query
                self.report_type = report_type
                self.parent_query = parent_query
                self.verbose = verbose
                self.report_source = report_source
                self.tone = tone
                self.websocket = websocket
                self.headers = headers
                self.conduct_called = False
                created.append(self)

            async def conduct_research(self):
                # simulate doing some async work
                self.conduct_called = True

            async def write_report(self):
                # return a predictable report object
                return {"fake_report": True, "query": self.query, "report_type": self.report_type}

        # Patch the GPTResearcher symbol used by ResearchAgent.research
        orig = ResearchAgent.research.__globals__.get("GPTResearcher")
        ResearchAgent.research.__globals__["GPTResearcher"] = DummyResearcher

        try:
            # Create an agent with specific websocket and headers to ensure they are passed through
            agent = ResearchAgent(websocket="ws-connection", stream_output=None, tone="agent-tone", headers={"agent": "hdr"})

            # Import asyncio dynamically to avoid top-level import requirement in this test file
            asyncio = __import__("asyncio")

            # Run the async research method and get the result
            result = asyncio.get_event_loop().run_until_complete(
                agent.research(query="test query",
                               research_report="research_report",
                               parent_query="parent-q",
                               verbose=False,
                               source="web",
                               tone="casual",
                               headers={"ignored": "yes"})
            )

            # Assertions: the dummy researcher was created and its methods were invoked via research()
            self.assertEqual(len(created), 1, "Expected exactly one DummyResearcher to be instantiated")
            inst = created[0]
            self.assertTrue(inst.conduct_called, "conduct_research should have been called on the researcher")
            # Check that constructor arguments were forwarded correctly
            self.assertEqual(inst.query, "test query")
            self.assertEqual(inst.report_type, "research_report")
            self.assertEqual(inst.parent_query, "parent-q")
            self.assertFalse(inst.verbose)
            self.assertEqual(inst.report_source, "web")
            self.assertEqual(inst.tone, "casual")
            # websocket and headers should come from the agent (self.websocket, self.headers)
            self.assertEqual(inst.websocket, "ws-connection")
            self.assertEqual(inst.headers, {"agent": "hdr"})

            # Check returned report is what write_report provided
            self.assertEqual(result, {"fake_report": True, "query": "test query", "report_type": "research_report"})
        finally:
            # restore original GPTResearcher to avoid side effects on other tests
            if orig is None:
                ResearchAgent.research.__globals__.pop("GPTResearcher", None)
            else:
                ResearchAgent.research.__globals__["GPTResearcher"] = orig
