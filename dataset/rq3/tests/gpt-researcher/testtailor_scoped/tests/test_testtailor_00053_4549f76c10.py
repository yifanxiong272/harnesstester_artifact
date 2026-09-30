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
        """Verify ReviserAgent stores websocket, stream_output and normalizes headers correctly."""
        # create dummy values
        dummy_ws = object()
        dummy_stream = lambda *args, **kwargs: "streamed"
        supplied_headers = {"Authorization": "Bearer token"}

        # Case 1: all arguments provided
        agent = ReviserAgent(websocket=dummy_ws, stream_output=dummy_stream, headers=supplied_headers)
        self.assertIs(agent.websocket, dummy_ws)
        self.assertIs(agent.stream_output, dummy_stream)
        self.assertEqual(agent.headers, supplied_headers)

        # Case 2: headers omitted -> should default to empty dict
        agent_default = ReviserAgent()
        self.assertIsNone(agent_default.websocket)
        self.assertIsNone(agent_default.stream_output)
        self.assertEqual(agent_default.headers, {})

        # Case 3: headers explicitly passed as None -> should normalize to empty dict
        agent_none_headers = ReviserAgent(websocket=dummy_ws, stream_output=dummy_stream, headers=None)
        self.assertIs(agent_none_headers.websocket, dummy_ws)
        self.assertIs(agent_none_headers.stream_output, dummy_stream)
        self.assertEqual(agent_none_headers.headers, {})
