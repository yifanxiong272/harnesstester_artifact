import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.cloud_events')
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
        """Ensure from_agent truncates done_output longer than MAX_STRING_LENGTH"""
        # Create fake components the method expects
        class FakeHistory:
            def __init__(self, text):
                self._text = text

            def final_result(self):
                return self._text

            def is_done(self):
                return True

        class FakeState:
            stopped = False
            paused = False

            def model_dump(self):
                return {"example": "state"}

        class FakeAuthClient:
            device_id = "dev-123"

        class FakeCloudSync:
            auth_client = FakeAuthClient()

        # Build a string longer than MAX_STRING_LENGTH (500_000)
        large_len = 500000 + 10
        large_output = "A" * large_len

        # Minimal agent with required attributes
        class FakeAgent:
            pass

        agent = FakeAgent()
        agent._task_start_time = 1  # presence is checked by hasattr
        agent.history = FakeHistory(large_output)
        agent.task_id = "task-xyz"
        agent.cloud_sync = FakeCloudSync()
        agent.state = FakeState()

        # Call the classmethod under test
        event = UpdateAgentTaskEvent.from_agent(agent)

        # Assertions: output was truncated to MAX_STRING_LENGTH and other fields set
        self.assertIsNotNone(event)
        # MAX_STRING_LENGTH expected to be 500000 per project constant
        self.assertIsNotNone(event.done_output)
        self.assertEqual(len(event.done_output), 500000)
        self.assertEqual(event.done_output, large_output[:500000])
        # finished_at should be set because history.is_done() returns True
        self.assertIsNotNone(event.finished_at)
        # device id propagated
        self.assertEqual(event.device_id, "dev-123")
        # stopped/paused default values from FakeState
        self.assertFalse(event.stopped)
        self.assertFalse(event.paused)
