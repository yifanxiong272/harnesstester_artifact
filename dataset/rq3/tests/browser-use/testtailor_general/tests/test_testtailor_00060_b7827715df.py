import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.browser.watchdogs.recording_watchdog')
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
        """Ensure on_BrowserConnectedEvent accesses browser_profile and returns when record_video_dir is falsy."""
        # Create simple dummy objects to act as the needed attributes
        class Dummy: 
            pass

        dummy_profile = Dummy()
        # Falsy record_video_dir should cause early return after accessing browser_profile
        dummy_profile.record_video_dir = None

        dummy_session = Dummy()
        dummy_session.browser_profile = dummy_profile

        fake_self = Dummy()
        fake_self.browser_session = dummy_session

        # Call the async method as an unbound function, passing our fake self and a dummy event (not used)
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(RecordingWatchdog.on_BrowserConnectedEvent(fake_self, None))

        # Should return None (no recording started)
        self.assertIsNone(result)
