import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.browser.watchdogs.popups_watchdog')
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
        """Ensure that when a target already has dialog listeners registered, the handler returns early."""
        # Prepare a target id that we will mark as already registered
        target_id = "target-123"

        # Backup class attributes to restore later
        orig_logger = getattr(PopupsWatchdog, "logger", None)
        orig_registered = getattr(PopupsWatchdog, "_dialog_listeners_registered", None)

        try:
            # Replace the class logger with a Mock so instance accesses it without needing __init__
            mock_logger = unittest.mock.Mock()
            PopupsWatchdog.logger = mock_logger

            # Ensure the class-level registered set contains our target so the instance will see it
            PopupsWatchdog._dialog_listeners_registered = {target_id}

            # Create an instance without running __init__
            wd = object.__new__(PopupsWatchdog)

            # Minimal event object with required attributes
            class Event:
                pass

            event = Event()
            event.target_id = target_id
            event.url = "about:blank"

            # Call the async handler
            import asyncio
            asyncio.run(wd.on_TabCreatedEvent(event))

            # Verify the early-return debug message was emitted
            mock_logger.debug.assert_any_call(f'Already registered dialog handlers for target {target_id}')

        finally:
            # Restore original class attributes to avoid side effects on other tests
            if orig_logger is None:
                try:
                    delattr(PopupsWatchdog, "logger")
                except Exception:
                    pass
            else:
                PopupsWatchdog.logger = orig_logger

            if orig_registered is None:
                try:
                    delattr(PopupsWatchdog, "_dialog_listeners_registered")
                except Exception:
                    pass
            else:
                PopupsWatchdog._dialog_listeners_registered = orig_registered
