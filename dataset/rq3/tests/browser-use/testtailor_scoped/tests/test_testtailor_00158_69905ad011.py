import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.telemetry.service')
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
        """Ensure ProductTelemetry.capture delegates to _direct_capture and calls posthog capture with merged properties."""
        import unittest.mock as mock

        # Local imports (allowed inside test body)
        from browser_use.telemetry.service import ProductTelemetry, POSTHOG_EVENT_SETTINGS

        # Create telemetry service and inject a mock posthog client so the capture path is exercised
        telemetry = ProductTelemetry()
        fake_client = mock.Mock()
        telemetry._posthog_client = fake_client

        # Fix the user id to a known value to assert it is propagated
        telemetry._curr_user_id = 'test-user-42'

        # Create a simple event-like object compatible with ProductTelemetry._direct_capture usage
        event = type('E', (), {})()
        event.name = 'test_event_name'
        event.properties = {'alpha': 1, 'beta': 'two'}

        # Call capture -> should call _direct_capture -> should call fake_client.capture(...)
        telemetry.capture(event)

        # Verify capture was invoked exactly once
        fake_client.capture.assert_called_once()
        _, kwargs = fake_client.capture.call_args

        # Assert expected keywords were passed
        self.assertIn('distinct_id', kwargs)
        self.assertIn('event', kwargs)
        self.assertIn('properties', kwargs)

        self.assertEqual(kwargs['distinct_id'], 'test-user-42')
        self.assertEqual(kwargs['event'], 'test_event_name')

        # Properties should be the merge of event.properties and POSTHOG_EVENT_SETTINGS
        expected_props = {**event.properties, **POSTHOG_EVENT_SETTINGS}
        self.assertEqual(kwargs['properties'], expected_props)
