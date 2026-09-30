import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.log.ui.web')
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
        payload = {"key": "value"}
        msg = mock_msg(payload)

        # Basic type and identity checks
        self.assertIsInstance(msg, Message)
        self.assertIs(msg.content, payload)

        # Field value checks
        self.assertEqual(msg.tag, "mock")
        self.assertEqual(msg.level, "INFO")
        self.assertEqual(msg.pid_trace, "000")
        self.assertEqual(msg.caller, "mock")

        # Timestamp should be a datetime and very recent
        self.assertIsInstance(msg.timestamp, datetime)
        now = datetime.now()
        diff = abs((now - msg.timestamp).total_seconds())
        self.assertLessEqual(diff, 1.0)
