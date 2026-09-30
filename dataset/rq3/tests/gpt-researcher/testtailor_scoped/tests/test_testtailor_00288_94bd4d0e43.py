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
        """Ensure run_initial_research extracts task, query and uses default source 'web' and calls stream_output."""
        # Prepare async helpers to attach to the agent
        async def fake_stream_output(stream_type, stage, message, websocket):
            # record that it was called and the arguments
            fake_stream_output.called = True
            fake_stream_output.args = (stream_type, stage, message, websocket)

        async def fake_research(query: str, research_report: str = "research_report",
                                parent_query: str = "", verbose=True, source="web", tone=None, headers=None):
            # capture parameters passed in and return a mock report
            fake_research.captured = {"query": query, "research_report": research_report,
                                      "parent_query": parent_query, "verbose": verbose,
                                      "source": source, "tone": tone, "headers": headers}
            return {"mock_report_for": query, "used_source": source}

        # Create agent with websocket and stream_output to avoid calling print_agent_output
        agent = ResearchAgent(websocket="ws_connection", stream_output=fake_stream_output, tone="neutral", headers={"h": "v"})
        # Patch the research method on this instance
        agent.research = fake_research

        # Provide research_state without 'source' to exercise defaulting to "web"
        research_state = {"task": {"query": "example query", "verbose": False}}

        # Run the async method and get result using __import__('asyncio') to avoid relying on a prior import
        loop = __import__('asyncio').get_event_loop()
        result = loop.run_until_complete(agent.run_initial_research(research_state))

        # Assertions
        self.assertIn("task", result)
        self.assertIs(result["task"], research_state["task"])
        self.assertIn("initial_research", result)
        self.assertEqual(result["initial_research"], {"mock_report_for": "example query", "used_source": "web"})
        # Ensure the fake_research captured source defaulted to "web"
        self.assertEqual(fake_research.captured["source"], "web")
        # Ensure stream_output was called instead of print_agent_output
        self.assertTrue(getattr(fake_stream_output, "called", False))
        # Validate the streaming message contains the query
        self.assertIn("example query", fake_stream_output.args[2])
