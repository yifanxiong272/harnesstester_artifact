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
        # Build a fake agent with the required attributes used by from_agent
        class DummyHistory:
            def __init__(self, text):
                self._text = text

            def final_result(self):
                return self._text

            def is_done(self):
                return True

        class DummyState:
            stopped = True
            paused = False

            def model_dump(self):
                return {"foo": "bar"}

        class DummyAuthClient:
            device_id = "device-123"

        class DummyCloudSync:
            auth_client = DummyAuthClient()

        agent = type("AgentLike", (), {})()
        # Ensure the attribute check passes
        agent._task_start_time = 1.0
        agent.task_id = "task-xyz"
        # Create a string longer than MAX_STRING_LENGTH (500_000 per project)
        long_text = "x" * 500001
        agent.history = DummyHistory(long_text)
        agent.state = DummyState()
        agent.cloud_sync = DummyCloudSync()

        # Call the classmethod under test
        event = UpdateAgentTaskEvent.from_agent(agent)

        # Assertions: done_output must be truncated to MAX_STRING_LENGTH (500_000)
        self.assertIsNotNone(event.done_output)
        self.assertEqual(len(event.done_output), 500000)
        # Other fields populated as expected from the fake agent
        self.assertEqual(event.id, str(agent.task_id))
        self.assertEqual(event.device_id, "device-123")
        self.assertTrue(event.stopped)
        self.assertFalse(event.paused)
        self.assertIsNotNone(event.finished_at)
        self.assertEqual(event.agent_state, {"foo": "bar"})
