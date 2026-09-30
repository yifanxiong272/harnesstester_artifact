import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('multi_agents.agents.researcher')
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
        """Verify ResearchAgent __init__ properly assigns websocket, stream_output, headers, and tone."""
        # Setup inputs
        ws = object()
        stream_fn = lambda *a, **k: None
        tone_val = "formal"

        # Case 1: headers is None -> should default to empty dict
        agent1 = ResearchAgent(websocket=ws, stream_output=stream_fn, tone=tone_val, headers=None)
        self.assertIs(agent1.websocket, ws)
        self.assertIs(agent1.stream_output, stream_fn)
        self.assertEqual(agent1.tone, tone_val)
        self.assertIsInstance(agent1.headers, dict)
        self.assertEqual(agent1.headers, {})  # default empty dict when None provided

        # Case 2: headers provided -> should use the provided object
        hdrs = {"Authorization": "Bearer token"}
        agent2 = ResearchAgent(websocket=ws, stream_output=stream_fn, tone=None, headers=hdrs)
        self.assertIs(agent2.websocket, ws)
        self.assertIs(agent2.stream_output, stream_fn)
        self.assertIs(agent2.headers, hdrs)  # should be the same dict object passed in
        self.assertIsNone(agent2.tone)
