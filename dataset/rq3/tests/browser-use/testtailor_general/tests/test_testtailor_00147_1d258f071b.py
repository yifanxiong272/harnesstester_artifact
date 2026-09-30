import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.browser.watchdogs.default_action_watchdog')
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
        """Ensure that when a downloads_watchdog is present, register_download_callbacks is called
        with the expected callback callables and that unregister is called on completion.
        """

        async def _test_coro():
            # Minimal dummy logger that records calls (no-op otherwise)
            class DummyLogger:
                def __init__(self):
                    self.records = []
                def debug(self, msg):
                    self.records.append(("debug", msg))
                def info(self, msg):
                    self.records.append(("info", msg))
                def warning(self, msg):
                    self.records.append(("warning", msg))

            # Dummy watchdog to capture register/unregister calls and the provided callbacks
            class DummyWatchdog:
                def __init__(self):
                    self.register_called = False
                    self.unregister_called = False
                    self.register_args = None
                    self.unregister_args = None

                def register_download_callbacks(self, on_start=None, on_progress=None, on_complete=None):
                    self.register_called = True
                    self.register_args = (on_start, on_progress, on_complete)

                def unregister_download_callbacks(self, on_start=None, on_progress=None, on_complete=None):
                    self.unregister_called = True
                    self.unregister_args = (on_start, on_progress, on_complete)

            # Prepare dummy "self" with required attributes used by the target method
            dummy_logger = DummyLogger()
            dummy_watchdog = DummyWatchdog()

            dummy_browser_session = type("BS", (), {})()
            dummy_browser_session._downloads_watchdog = dummy_watchdog

            dummy_self = type("S", (), {})()
            dummy_self.logger = dummy_logger
            dummy_self.browser_session = dummy_browser_session

            # Reference the unbound async method from the class under test
            func = DefaultActionWatchdog._execute_click_with_download_detection

            # Create a simple click coroutine that completes immediately (returns None)
            async def click_coro():
                return None

            # Call the method with tiny timeouts so it won't hang waiting for downloads
            result = await func(
                dummy_self,
                click_coro(),
                download_start_timeout=0.01,
                download_complete_timeout=0.01,
            )

            # Assertions: register should have been called and provided callbacks should be callables
            self.assertTrue(dummy_watchdog.register_called, "Expected register_download_callbacks to be called")
            self.assertIsNotNone(dummy_watchdog.register_args, "Expected register args to be captured")
            on_start, on_progress, on_complete = dummy_watchdog.register_args
            self.assertTrue(callable(on_start), "on_start should be callable")
            self.assertTrue(callable(on_progress), "on_progress should be callable")
            self.assertTrue(callable(on_complete), "on_complete should be callable")

            # Finally block should have unregistered callbacks
            self.assertTrue(dummy_watchdog.unregister_called, "Expected unregister_download_callbacks to be called")

            # The function returns None when click_metadata is not a dict (we returned None)
            self.assertIsNone(result)

        asyncio.get_event_loop().run_until_complete(_test_coro())
