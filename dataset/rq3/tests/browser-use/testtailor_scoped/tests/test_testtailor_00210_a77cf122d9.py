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
        """Ensure _direct_capture returns early when _posthog_client is None."""
        from browser_use.telemetry.service import ProductTelemetry
        from browser_use.telemetry.views import BaseTelemetryEvent

        telemetry = ProductTelemetry()
        # Force the client to None to hit the early-return branch
        telemetry._posthog_client = None

        class DummyEvent(BaseTelemetryEvent):
            @property
            def name(self) -> str:
                return "dummy_event"

            @property
            def properties(self) -> dict:
                return {"k": "v"}

        event = DummyEvent()

        # Should return None and not raise when posthog client is missing
        result_direct = telemetry._direct_capture(event)
        self.assertIsNone(result_direct)

        # Public capture delegates to _direct_capture and should behave the same
        result_public = telemetry.capture(event)
        self.assertIsNone(result_public)
