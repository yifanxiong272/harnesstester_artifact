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
        """Parse browser_created event into BrowserCreatedData"""
        event = {
            "type": "browser_created",
            "data": {
                "session_id": "sess-123",
                "live_url": "https://example.com/live/sess-123",
                "status": "created"
            },
            "timestamp": "2026-01-01T00:00:00Z"
        }
        event_json = json.dumps(event)
        sse_event = SSEEvent.from_json(event_json)

        # Type and helper guard
        self.assertEqual(sse_event.type, SSEEventType.BROWSER_CREATED)
        self.assertTrue(sse_event.is_browser_created())

        # Data model checks
        self.assertIsInstance(sse_event.data, BrowserCreatedData)
        self.assertEqual(sse_event.data.session_id, "sess-123")
        self.assertEqual(sse_event.data.live_url, "https://example.com/live/sess-123")
        self.assertEqual(sse_event.data.status, "created")

        # Timestamp preserved
        self.assertEqual(sse_event.timestamp, "2026-01-01T00:00:00Z")
