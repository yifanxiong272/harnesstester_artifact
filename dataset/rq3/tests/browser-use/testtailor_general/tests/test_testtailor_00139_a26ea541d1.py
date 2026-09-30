import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.screenshots.service')
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
        """Return None when screenshot_path is falsy (empty string)."""
        service = ScreenshotService('.')  # use current directory, no tempfile needed
        coro = service.get_screenshot('')  # obtain coroutine without awaiting
        try:
            # Drive the coroutine until it returns. For an async def that
            # returns immediately (no awaits before return), send(None)
            # will raise StopIteration with the return value.
            coro.send(None)
            self.fail("Coroutine did not return as expected")
        except StopIteration as e:
            self.assertIsNone(e.value)
