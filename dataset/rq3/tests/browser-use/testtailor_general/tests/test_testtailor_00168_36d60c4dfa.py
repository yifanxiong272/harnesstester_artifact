import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.browser.watchdogs.local_browser_watchdog')
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
        """Ensure on_BrowserKillEvent logs the expected debug message."""
        debug_messages = []

        class DummyLogger:
            def debug(self, msg, *args, **kwargs):
                debug_messages.append(msg)

            def error(self, msg, *args, **kwargs):
                debug_messages.append(f'ERROR: {msg}')

            def warning(self, msg, *args, **kwargs):
                debug_messages.append(f'WARN: {msg}')

        # Backup any existing class-level logger and replace it so instance access works
        original_class_logger = getattr(LocalBrowserWatchdog, 'logger', None)
        LocalBrowserWatchdog.logger = DummyLogger()

        try:
            # Create instance without invoking BaseModel __init__
            watchdog = object.__new__(LocalBrowserWatchdog)

            # Provide the minimal attributes used by on_BrowserKillEvent
            watchdog._subprocess = None
            watchdog._temp_dirs_to_cleanup = []
            watchdog._original_user_data_dir = None

            # Call the async handler
            asyncio.run(watchdog.on_BrowserKillEvent(BrowserKillEvent()))

            # Assert the initial debug log was emitted
            expected = '[LocalBrowserWatchdog] Killing local browser process'
            self.assertTrue(
                any(expected in m for m in debug_messages),
                f"Expected log message not found in {debug_messages}"
            )
        finally:
            # Restore original class logger to avoid side effects
            if original_class_logger is not None:
                LocalBrowserWatchdog.logger = original_class_logger
            else:
                # If there was no original, delete the attribute we added
                try:
                    delattr(LocalBrowserWatchdog, 'logger')
                except Exception:
                    pass
