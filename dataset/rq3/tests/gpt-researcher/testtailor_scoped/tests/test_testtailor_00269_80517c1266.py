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
        """Ensure stream_output is awaited when websocket and stream_output are present."""
        agent = WriterAgent(websocket=object(), stream_output=None)

        # capture stream_output calls
        stream_calls = []

        async def fake_stream_output(kind, tag, message, websocket):
            stream_calls.append((kind, tag, message, websocket))

        # bind the fake stream_output and a fake write_sections to the agent
        agent.stream_output = fake_stream_output

        async def fake_write_sections(self, research_state):
            # return a simple layout content dict
            return {"introduction": "Intro text", "conclusion": "Conclusion text"}

        # bind fake_write_sections as an instance method
        agent.write_sections = fake_write_sections.__get__(agent, WriterAgent)

        research_state = {
            "title": "Test Title",
            "research_data": {"some": "data"},
            "task": {
                "follow_guidelines": False,
                "verbose": False,
                "model": "test-model",
                "guidelines": None,
            },
        }

        # use __import__ to avoid adding an import statement at top-level
        asyncio = __import__("asyncio")
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(agent.run(research_state))

        # Assert stream_output was called for the initial writing_report log
        self.assertGreaterEqual(len(stream_calls), 1)
        first_call = stream_calls[0]
        self.assertEqual(first_call[0], "logs")
        self.assertEqual(first_call[1], "writing_report")
        self.assertEqual(
            first_call[2], "Writing final research report based on research data..."
        )
        # websocket passed through should be the same object as agent.websocket
        self.assertIs(first_call[3], agent.websocket)

        # The returned result should include headers from get_headers
        self.assertIn("headers", result)
        self.assertEqual(result["headers"]["title"], research_state["title"])
