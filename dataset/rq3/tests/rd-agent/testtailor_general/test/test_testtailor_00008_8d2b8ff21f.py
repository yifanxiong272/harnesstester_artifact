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
        obj = {"key": "value"}
        msg = mock_msg(obj)

        # Basic structure and types
        self.assertIsInstance(msg, Message)
        self.assertIsInstance(msg.timestamp, datetime)

        # Fixed fields set by mock_msg
        self.assertEqual(msg.tag, "mock")
        self.assertEqual(msg.level, "INFO")
        self.assertEqual(msg.pid_trace, "000")
        self.assertEqual(msg.caller, "mock")

        # Content should be exactly the object passed in
        self.assertIs(msg.content, obj)

        # Timestamp should be very recent (allowing up to 1 second)
        now = datetime.now()
        delta = (now - msg.timestamp).total_seconds()
        self.assertGreaterEqual(delta, 0)
        self.assertLessEqual(delta, 1)
