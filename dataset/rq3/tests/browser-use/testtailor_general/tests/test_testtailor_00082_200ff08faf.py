import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.browser.watchdogs.captcha_watchdog')
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
        """Ensure on_BrowserConnectedEvent returns early when handlers already registered."""
        # Create a bare CaptchaWatchdog without running Pydantic validation
        watchdog = CaptchaWatchdog.construct()
        # Mark handlers as already registered to hit the early-return branch
        watchdog._cdp_handlers_registered = True

        # Attach a minimal browser_session that provides a logger used by the watchdog.logger property
        class DummySession:
            pass

        session = DummySession()
        session.logger = Mock()
        watchdog.browser_session = session

        # Sanity pre-conditions
        self.assertTrue(watchdog._cdp_handlers_registered)

        # Create a minimal event instance
        event = BrowserConnectedEvent(cdp_url='ws://localhost')

        # Run the async handler; should return quickly and not raise
        asyncio.get_event_loop().run_until_complete(watchdog.on_BrowserConnectedEvent(event))

        # Verify the early-return debug log was emitted via the session logger
        session.logger.debug.assert_called_once_with('CaptchaWatchdog: CDP handlers already registered, skipping')
