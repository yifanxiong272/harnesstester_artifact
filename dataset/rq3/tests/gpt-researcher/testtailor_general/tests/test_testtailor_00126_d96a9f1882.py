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
        """Test plan_research uses call_model and returns mapped plan fields."""
        async def fake_call_model(*, prompt, model, response_format):
            # Basic sanity checks on prompt structure to ensure proper creation
            assert isinstance(prompt, list)
            assert any(p.get("role") == "system" for p in prompt)
            assert response_format == "json"
            return {
                "title": "Research on AI",
                "date": "02/02/2022",
                "sections": ["Background", "Methods"]
            }

        def fake_print_agent_output(message, agent=None):
            # record that printing was attempted
            fake_print_agent_output.called = True

        # Patch the module where EditorAgent is defined so its call_model/print_agent_output are replaced
        import sys
        import asyncio

        module = sys.modules[EditorAgent.__module__]
        module.call_model = fake_call_model
        module.print_agent_output = fake_print_agent_output

        # Prepare test input
        agent = EditorAgent()
        research_state = {
            "initial_research": "Study about transformer models",
            "task": {
                "include_human_feedback": False,
                "max_sections": 2,
                "model": "gpt-test"
            },
            "human_feedback": None,
        }

        # Ensure flag initialized
        fake_print_agent_output.called = False

        # Run the async method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(agent.plan_research(research_state))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        # Verify outputs are mapped correctly from the model response
        self.assertEqual(result["title"], "Research on AI")
        self.assertEqual(result["date"], "02/02/2022")
        self.assertEqual(result["sections"], ["Background", "Methods"])
        self.assertTrue(getattr(fake_print_agent_output, "called", False))
