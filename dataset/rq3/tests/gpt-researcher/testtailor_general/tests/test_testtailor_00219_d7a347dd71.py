import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('multi_agents.agents.editor')
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
        """Test run_parallel_research returns gathered drafts for given sections."""
        agent = EditorAgent()  # use defaults; websocket/stream_output not required for this test

        # Fake chain that exposes an async ainvoke method
        class FakeChain:
            async def ainvoke(self, task_input, config=None):
                # return a dict with a 'draft' key as expected by the code under test
                return {"draft": f"draft for {task_input.get('topic')}"}

        # Fake workflow whose compile() returns the fake chain
        class FakeWorkflow:
            def compile(self):
                return FakeChain()

        # Patch methods on the agent to control behavior and avoid external dependencies
        agent._initialize_agents = lambda: {"research": None, "reviewer": None, "reviser": None}
        agent._create_workflow = lambda: FakeWorkflow()
        agent._log_parallel_research = lambda queries: None

        def fake_create_task_input(research_state, query, title):
            return {
                "task": research_state.get("task"),
                "topic": query,
                "title": title,
                "headers": agent.headers,
            }

        agent._create_task_input = fake_create_task_input

        research_state = {
            "sections": ["Introduction to X", "Related Work on X", "Future Directions for X"],
            "title": "Research on X",
            "task": {"model": "test-model"},
        }

        result = asyncio.run(agent.run_parallel_research(research_state))

        expected = {
            "research_data": [
                "draft for Introduction to X",
                "draft for Related Work on X",
                "draft for Future Directions for X",
            ]
        }

        self.assertEqual(result, expected)
