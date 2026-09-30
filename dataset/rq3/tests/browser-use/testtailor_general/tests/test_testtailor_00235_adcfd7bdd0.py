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
        """Ensure on_TabClosedEvent returns immediately when _stopping is True"""
        import asyncio

        # Create AboutBlankWatchdog instance without running full initialization
        watchdog = AboutBlankWatchdog.__new__(AboutBlankWatchdog)
        # pydantic's __setattr__ expects __pydantic_fields_set__ to exist when setting attributes
        setattr(watchdog, '__pydantic_fields_set__', set())

        # Set the stopping flag so the method should early-return
        watchdog._stopping = True

        # Do NOT provide a browser_session to ensure method does not attempt to access it.
        # Call the async method and ensure it returns None (early return)
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(AboutBlankWatchdog.on_TabClosedEvent(watchdog, object()))
        finally:
            loop.close()

        self.assertIsNone(result)
