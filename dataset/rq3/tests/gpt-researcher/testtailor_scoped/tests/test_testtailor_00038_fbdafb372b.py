import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('multi_agents.agents.reviewer')
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
        # Case 1: default construction -> websocket and stream_output should be None, headers should default to a dict
        agent_default = ReviewerAgent()
        self.assertIsNone(agent_default.websocket)
        self.assertIsNone(agent_default.stream_output)
        self.assertIsInstance(agent_default.headers, dict)
        self.assertEqual(agent_default.headers, {})

        # Mutating the default headers on this instance should work (ensure it's a real dict)
        agent_default.headers["new"] = "value"
        self.assertEqual(agent_default.headers, {"new": "value"})

        # Case 2: provide explicit websocket, stream_output and non-empty headers
        ws = object()
        def stream_stub(event, name, message, websocket):
            return (event, name, message, websocket)

        provided_headers = {"Authorization": "token"}
        agent = ReviewerAgent(websocket=ws, stream_output=stream_stub, headers=provided_headers)

        # Check assignments preserved
        self.assertIs(agent.websocket, ws)
        self.assertIs(agent.stream_output, stream_stub)
        self.assertEqual(agent.headers, provided_headers)
        # If a non-empty dict was provided, the same object should be used
        self.assertIs(agent.headers, provided_headers)
