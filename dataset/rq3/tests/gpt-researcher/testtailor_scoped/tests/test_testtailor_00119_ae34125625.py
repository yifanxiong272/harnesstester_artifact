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
        """Test EditorAgent.plan_research calls call_model and returns the parsed plan."""
        agent = EditorAgent()

        research_state = {
            "initial_research": "A short summary about advances in AI safety research.",
            "task": {
                "include_human_feedback": True,
                "max_sections": 3,
                "model": "gpt-test-model",
            },
            "human_feedback": "Emphasize robustness and ethics.",
        }

        # Prepare the mocked plan the model would return
        expected_plan = {
            "title": "AI Safety: Robustness and Ethics",
            "date": "23/08/2026",
            "sections": ["Robustness Approaches", "Ethical Considerations", "Evaluation Metrics"],
        }

        module = EditorAgent.__module__

        # Patch call_model (async) and print_agent_output to isolate the test
        mock_call = AsyncMock(return_value=expected_plan)
        with patch(f"{module}.call_model", new=mock_call), patch(f"{module}.print_agent_output"):
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(agent.plan_research(research_state))

        # Verify the result matches the mocked plan structure
        self.assertEqual(result["title"], expected_plan["title"])
        self.assertEqual(result["date"], expected_plan["date"])
        self.assertEqual(result["sections"], expected_plan["sections"])
        # Ensure call_model was awaited once
        mock_call.assert_awaited_once()
