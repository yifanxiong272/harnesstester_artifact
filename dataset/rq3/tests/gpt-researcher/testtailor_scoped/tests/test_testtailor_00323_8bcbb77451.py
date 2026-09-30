import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('multi_agents.agents.writer')
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
        """Ensure run() takes the branch where websocket/stream_output are not set
        (so print_agent_output path is used) and returns combined layout and headers."""
        agent = WriterAgent()  # websocket and stream_output default to None

        async def fake_write_sections(self, research_state):
            # Return a predictable layout content to avoid calling external model
            return {"introduction": "Intro text", "conclusion": "Conclusion text"}

        # Bind the async stub to the instance to replace the real write_sections
        agent.write_sections = fake_write_sections.__get__(agent, WriterAgent)

        research_state = {
            "title": "Test Report",
            "research_data": [{"source": "s1", "text": "data"}],
            "task": {
                "follow_guidelines": False,  # avoid revise_headers / call_model
                "verbose": False,
                "model": "test-model",
                "guidelines": "",
            },
        }

        # Run the async method and get result without relying on a pre-imported asyncio name
        try:
            import asyncio

            try:
                result = asyncio.get_event_loop().run_until_complete(agent.run(research_state))
            except RuntimeError:
                # If no running loop is available, use asyncio.run as a fallback
                result = asyncio.run(agent.run(research_state))
        except Exception as e:
            # Fallback: use anyio if available (covers other test environments)
            try:
                import anyio

                result = anyio.run(agent.run, research_state)
            except Exception:
                raise e

        # Expected headers come from get_headers()
        expected_headers = agent.get_headers(research_state)

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("introduction"), "Intro text")
        self.assertEqual(result.get("conclusion"), "Conclusion text")
        self.assertEqual(result.get("headers"), expected_headers)
