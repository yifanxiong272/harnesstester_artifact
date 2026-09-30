import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('multi_agents.agents.reviser')
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
        """complete the test case here"""
        agent = ReviserAgent()

        # record calls to the stream_output async function
        called = {}

        async def fake_revise_draft(draft_state):
            # simulate the revise_draft returning the expected structure
            return {"draft": "revised content", "revision_notes": "these are the notes"}

        async def fake_stream_output(category, name, message, websocket):
            called["args"] = (category, name, message, websocket)
            return None

        # Attach our fakes to the agent and ensure websocket is truthy
        agent.revise_draft = fake_revise_draft
        agent.stream_output = fake_stream_output
        agent.websocket = "fake_ws"

        draft_state = {
            "task": {"verbose": True, "model": "any-model"},
            "review": "some review",
            "draft": "original draft",
        }

        # Use __import__ to obtain asyncio without adding an import statement at top-level
        asyncio = __import__("asyncio")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(agent.run(draft_state))
        finally:
            loop.close()

        # verify the run result
        self.assertEqual(result["draft"], "revised content")
        self.assertEqual(result["revision_notes"], "these are the notes")

        # verify stream_output was called with the expected arguments
        self.assertIn("args", called)
        category, name, message, websocket = called["args"]
        self.assertEqual(category, "logs")
        self.assertEqual(name, "revision_notes")
        self.assertEqual(message, "Revision notes: these are the notes")
        self.assertEqual(websocket, "fake_ws")
