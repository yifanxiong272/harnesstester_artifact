import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.browser.watchdogs.crash_watchdog')
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
        """Verify NetworkRequestTracker stores constructor arguments on the instance."""
        # first case: resource_type provided
        request_id = "req-123"
        start_time = 1625079600.5
        url = "https://example.com/path"
        method = "GET"
        resource_type = "document"

        tracker = NetworkRequestTracker(request_id, start_time, url, method, resource_type)

        self.assertEqual(tracker.request_id, request_id)
        self.assertEqual(tracker.start_time, start_time)
        self.assertEqual(tracker.url, url)
        self.assertEqual(tracker.method, method)
        self.assertEqual(tracker.resource_type, resource_type)

        # second case: resource_type omitted / None
        request_id2 = "req-456"
        start_time2 = 0.0
        url2 = "http://localhost/"
        method2 = "POST"

        tracker2 = NetworkRequestTracker(request_id2, start_time2, url2, method2)

        self.assertEqual(tracker2.request_id, request_id2)
        self.assertEqual(tracker2.start_time, start_time2)
        self.assertEqual(tracker2.url, url2)
        self.assertEqual(tracker2.method, method2)
        self.assertIsNone(tracker2.resource_type)
