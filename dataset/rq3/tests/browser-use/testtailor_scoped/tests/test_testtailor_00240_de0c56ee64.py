import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.beta.service')
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
        """Verify _laminar_set_span_attributes calls Laminar.set_span_attributes on safe attrs
        and gracefully logs (without raising) when Laminar.set_span_attributes raises."""
        # import inside test (imports are provided by the test harness)
        import browser_use.beta.service as beta_service

        # preserve originals to restore later
        orig_Laminar = getattr(beta_service, "Laminar", None)
        orig_logger = getattr(beta_service, "logger", None)

        try:
            # --- Case 1: successful set_span_attributes is invoked with only safe attributes ---
            called = {}

            class FakeLaminarGood:
                @staticmethod
                def is_initialized():
                    return True

                @staticmethod
                def set_span_attributes(attrs):
                    # record what was passed
                    called["attrs"] = dict(attrs)

            beta_service.Laminar = FakeLaminarGood

            # Replace logger with one that would fail the test if erroneously called
            class DummyLogger:
                def debug(self, *args, **kwargs):
                    raise AssertionError("logger.debug should not be called on successful set_span_attributes")

            beta_service.logger = DummyLogger()

            # Provide a mix of safe and unsafe attribute types; only safe types should be forwarded
            beta_service._laminar_set_span_attributes({"ok_str": "yes", "ok_int": 7, "bad_list": [1, 2], "ok_float": 1.5})

            # verify only safe attributes reached Laminar.set_span_attributes
            self.assertIn("attrs", called)
            self.assertEqual(called["attrs"], {"ok_str": "yes", "ok_int": 7, "ok_float": 1.5})

            # --- Case 2: set_span_attributes raises => should be caught and logger.debug called ---
            class FakeLaminarBad:
                @staticmethod
                def is_initialized():
                    return True

                @staticmethod
                def set_span_attributes(attrs):
                    raise RuntimeError("boom!")

            beta_service.Laminar = FakeLaminarBad

            logs = []

            class RecordingLogger:
                def debug(self, message, *args, **kwargs):
                    # capture the message and exc_info flag if present
                    logs.append({"message": message, "exc_info": kwargs.get("exc_info", None), "args": args})

            beta_service.logger = RecordingLogger()

            # Call with a simple safe attribute; the exception from set_span_attributes should be swallowed
            # and logger.debug should be invoked.
            beta_service._laminar_set_span_attributes({"trace_id": "trace-123"})

            # Assert logger.debug was called and included the expected message and exc_info=True
            self.assertTrue(logs, "Expected logger.debug to be called when Laminar.set_span_attributes raises")
            last = logs[-1]
            self.assertIn("Failed to set Laminar span attributes", last["message"])
            self.assertTrue(last["exc_info"] is True)
        finally:
            # restore originals
            beta_service.Laminar = orig_Laminar
            beta_service.logger = orig_logger
