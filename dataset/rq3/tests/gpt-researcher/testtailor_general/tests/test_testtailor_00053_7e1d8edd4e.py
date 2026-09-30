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
        """Verify ReviewerAgent.__init__ sets attributes and handles headers defaulting correctly."""
        # Case 1: headers is None -> should default to an empty dict (content equal)
        websocket = object()

        def dummy_stream_output(*args, **kwargs):
            return "streamed"

        agent = ReviewerAgent(websocket=websocket, stream_output=dummy_stream_output, headers=None)

        self.assertIs(agent.websocket, websocket)
        self.assertIs(agent.stream_output, dummy_stream_output)
        self.assertEqual(agent.headers, {})  # headers content should be empty dict when None provided

        # Case 2: headers provided (non-empty) -> should use the provided dict object (same identity)
        headers = {"Authorization": "Bearer token"}
        agent2 = ReviewerAgent(websocket=None, stream_output=None, headers=headers)

        self.assertIs(agent2.websocket, None)
        self.assertIs(agent2.stream_output, None)
        self.assertIs(agent2.headers, headers)  # should keep the same dict object when it's truthy

        # Case 3: explicitly passing an empty dict -> __init__ uses `headers or {}` so a new dict is created
        empty_headers = {}
        agent3 = ReviewerAgent(headers=empty_headers)
        self.assertEqual(agent3.headers, {})           # content should be an empty dict
        self.assertIsNot(agent3.headers, empty_headers)  # but not the same object because empty dict is falsy
