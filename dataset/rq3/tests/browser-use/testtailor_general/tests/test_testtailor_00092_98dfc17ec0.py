import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.browser.watchdogs.aboutblank_watchdog')
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
        """When an about:blank tab is created, the watchdog should show the DVD screensaver on about:blank tabs."""
        # Create an instance without running any initialization logic
        watchdog = AboutBlankWatchdog.__new__(AboutBlankWatchdog)

        # Create a recorder callable that returns an awaitable which completes immediately.
        class Recorder:
            def __init__(self):
                self.called = False

            def __call__(self):
                # Mark that the callable was invoked
                self.called = True

                # Immediate awaitable (no yields) so it completes synchronously when driven.
                class Immediate:
                    def __await__(self_inner):
                        if False:
                            yield None
                        return None

                return Immediate()

        recorder = Recorder()
        watchdog._show_dvd_screensaver_on_about_blank_tabs = recorder

        # Construct the event that should trigger the branch
        event = TabCreatedEvent(target_id='target-1', url='about:blank')

        # Manually drive the coroutine without importing asyncio:
        coro = watchdog.on_TabCreatedEvent(event)
        try:
            # Start the coroutine; this will yield the awaitable returned by our recorder
            awaitable = coro.send(None)
            # Drive the inner awaitable to completion
            inner_iter = awaitable.__await__()
            try:
                inner_iter.send(None)
                inner_result = None
            except StopIteration as e:
                inner_result = e.value
            # Resume the outer coroutine with the inner result
            try:
                coro.send(inner_result)
            except StopIteration:
                # Normal completion
                pass
        except StopIteration:
            # Coroutine completed without awaiting anything
            pass

        # Ensure the recorder was invoked (i.e., the method to show the DVD screensaver was called)
        self.assertTrue(recorder.called)
