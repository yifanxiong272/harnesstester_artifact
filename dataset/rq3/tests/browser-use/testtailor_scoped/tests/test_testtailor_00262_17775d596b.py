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
        """Test that _direct_capture calls posthog.capture and logs on exception."""
        from dataclasses import dataclass
        from browser_use.telemetry.views import BaseTelemetryEvent
        import browser_use.telemetry.service as telemetry_module
        from browser_use.telemetry.service import ProductTelemetry

        # Dummy event implementing BaseTelemetryEvent
        @dataclass
        class DummyEvent(BaseTelemetryEvent):
            model: str = 'gpt-test'
            count: int = 1

            @property
            def name(self) -> str:
                return 'test_event'

        # Fake PostHog client: record call then raise to exercise the except branch
        class FakePosthogClient:
            def __init__(self):
                self.recorded = None

            def capture(self, *, distinct_id, event, properties):
                self.recorded = {'distinct_id': distinct_id, 'event': event, 'properties': properties}
                raise RuntimeError('boom')

        # Temporarily replace ProductTelemetry.__init__ so we can instantiate without side effects
        orig_init = ProductTelemetry.__init__
        ProductTelemetry.__init__ = lambda self: None
        try:
            telemetry = ProductTelemetry()
        finally:
            ProductTelemetry.__init__ = orig_init

        # Attach fake client and a known user id
        fake_client = FakePosthogClient()
        telemetry._posthog_client = fake_client
        telemetry._curr_user_id = 'user-1234'

        # Capture logger.error calls
        logged = {}
        orig_logger_error = telemetry_module.logger.error

        def fake_logger_error(msg, *args, **kwargs):
            # record the formatted message or the first argument
            try:
                logged['msg'] = msg % args if args else msg
            except Exception:
                logged['msg'] = str(msg)

        telemetry_module.logger.error = fake_logger_error

        try:
            # Invoke target method
            event = DummyEvent()
            telemetry._direct_capture(event)

            # Verify PostHog client was invoked
            assert fake_client.recorded is not None, "PostHog client.capture was not invoked"
            assert fake_client.recorded['distinct_id'] == 'user-1234'
            assert fake_client.recorded['event'] == 'test_event'

            props = fake_client.recorded['properties']
            # Should include our event fields
            assert props.get('model') == 'gpt-test'
            assert props.get('count') == 1
            # Should include posthog settings key (best-effort check)
            assert 'process_person_profile' in props
            assert props['process_person_profile'] is True

            # Verify logging of the exception occurred
            assert 'Failed to send telemetry event test_event' in logged.get('msg', '')
            assert 'boom' in logged.get('msg', '')
        finally:
            # Restore logger to avoid side effects
            telemetry_module.logger.error = orig_logger_error
