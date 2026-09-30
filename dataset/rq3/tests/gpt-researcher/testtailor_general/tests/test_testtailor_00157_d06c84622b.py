import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('multi_agents.agents.human')
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
        """Ensure review_plan returns expected defaults when human feedback is not requested."""
        async def _run():
            agent = HumanAgent()  # websocket and stream_output default to None
            research_state = {
                "task": {"include_human_feedback": False},
                "sections": ["section1", "section2"],
            }
            return await agent.review_plan(research_state)

        result = __import__("asyncio").run(_run())
        self.assertIsInstance(result, dict)
        self.assertIn("human_feedback", result)
        self.assertIn("plan_revision_count", result)
        self.assertIsNone(result["human_feedback"])
        self.assertEqual(result["plan_revision_count"], 0)
