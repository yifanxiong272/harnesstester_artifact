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
        """Ensure ResearchAgent.research constructs a GPTResearcher, runs conduct_research and write_report, and returns the report."""
        # Prepare a dummy GPTResearcher to patch into the ResearchAgent.research globals
        class DummyResearcher:
            last_instance = None

            def __init__(self, query, report_type, parent_query, verbose, report_source, tone, websocket, headers):
                DummyResearcher.last_instance = self
                self.query = query
                self.report_type = report_type
                self.parent_query = parent_query
                self.verbose = verbose
                self.report_source = report_source
                self.tone = tone
                self.websocket = websocket
                self.headers = headers
                self.conduct_called = False

            async def conduct_research(self):
                # simulate doing some async work
                self.conduct_called = True

            async def write_report(self):
                return f"REPORT:{self.query}"

        # Patch the GPTResearcher name in the ResearchAgent.research function globals
        func_globals = ResearchAgent.research.__globals__
        original_gpt = func_globals.get("GPTResearcher", None)
        func_globals["GPTResearcher"] = DummyResearcher

        # Create an agent with specific headers to ensure they are passed through
        agent_headers = {"auth": "token"}
        agent = ResearchAgent(websocket="ws", stream_output=None, tone="formal", headers=agent_headers)

        # Run the async research method
        import asyncio
        old_loop = None
        try:
            try:
                old_loop = asyncio.get_event_loop()
            except RuntimeError:
                old_loop = None
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                report = loop.run_until_complete(
                    agent.research(query="my query", research_report="research_report",
                                   parent_query="parent q", verbose=False, source="web", tone="casual", headers={"x": "y"})
                )
            finally:
                loop.close()
                # restore previous event loop if existed
                if old_loop is not None:
                    asyncio.set_event_loop(old_loop)
                else:
                    try:
                        asyncio.set_event_loop(None)
                    except Exception:
                        pass

            # Assertions
            self.assertEqual(report, "REPORT:my query")
            inst = DummyResearcher.last_instance
            self.assertIsNotNone(inst, "GPTResearcher was not instantiated")
            self.assertTrue(inst.conduct_called, "conduct_research was not called")
            self.assertEqual(inst.report_type, "research_report")
            self.assertEqual(inst.parent_query, "parent q")
            self.assertEqual(inst.report_source, "web")
            # headers passed should be the agent's headers (ResearchAgent uses self.headers when constructing GPTResearcher)
            self.assertEqual(inst.headers, agent_headers)
            self.assertEqual(inst.tone, "casual")
            self.assertEqual(inst.websocket, "ws")
        finally:
            # Restore original GPTResearcher in globals
            if original_gpt is not None:
                func_globals["GPTResearcher"] = original_gpt
            else:
                func_globals.pop("GPTResearcher", None)
