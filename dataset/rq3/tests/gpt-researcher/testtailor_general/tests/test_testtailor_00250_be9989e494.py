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
        """Test that HumanAgent routes through websocket + stream_output branch and parses response."""
        # setup a mock websocket that matches the structure used in the method:
        # agent.websocket.websocket.receive_text() -> returns JSON string
        class DummyInner:
            async def receive_text(self):
                return '{"type":"human_feedback","content":"Looks good"}'

        class DummyWebsocketWrapper:
            def __init__(self):
                self.websocket = DummyInner()

        calls = []

        async def mock_stream_output(event, subtype, content, websocket):
            # record the call arguments for assertions
            calls.append((event, subtype, content, websocket))

        agent = HumanAgent(websocket=DummyWebsocketWrapper(), stream_output=mock_stream_output)

        research_state = {
            "task": {"include_human_feedback": True},
            "sections": ["sec1", "sec2"],
            "plan_revision_count": 0,
        }

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(agent.review_plan(research_state))

        # stream_output should have been called once with the expected event and subtype
        self.assertEqual(len(calls), 1)
        event, subtype, content, ws_passed = calls[0]
        self.assertEqual(event, "human_feedback")
        self.assertEqual(subtype, "request")
        # content should include the layout representation
        self.assertIn("sec1", content)
        self.assertIn("sec2", content)
        # websocket passed to stream_output should be the same wrapper object
        self.assertIs(ws_passed, agent.websocket)

        # the returned human_feedback should be parsed from the JSON and revision count incremented
        self.assertEqual(result["human_feedback"], "Looks good")
        self.assertEqual(result["plan_revision_count"], 1)
