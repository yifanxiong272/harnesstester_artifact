import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.sandbox.views')
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
        """Ensure from_json parses type, data and timestamp correctly for a log event"""
        # JSON string for a log event
        event_json = (
            '{"type":"log",'
            '"data":{"message":"hello","level":"warning"},'
            '"timestamp":"2021-01-01T00:00:00Z"}'
        )

        event = SSEEvent.from_json(event_json)

        # Type should be the LOG enum
        self.assertEqual(event.type, SSEEventType.LOG)
        # Data should be parsed into LogData
        self.assertIsInstance(event.data, LogData)
        self.assertEqual(event.data.message, "hello")
        self.assertEqual(event.data.level, "warning")
        # Timestamp should be preserved
        self.assertEqual(event.timestamp, "2021-01-01T00:00:00Z")
        # Type guard helper should work
        self.assertTrue(event.is_log())
