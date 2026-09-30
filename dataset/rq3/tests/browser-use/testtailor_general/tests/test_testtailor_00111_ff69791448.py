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
        """from_agent should raise if agent lacks _task_start_time attribute"""
        class DummyAgent:
            # Intentionally do not define _task_start_time
            pass

        agent = DummyAgent()

        with self.assertRaises(ValueError) as cm:
            UpdateAgentTaskEvent.from_agent(agent)

        self.assertEqual(str(cm.exception), 'Agent must have _task_start_time attribute')
