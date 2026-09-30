import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.actor.page')
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
        """When Page._mouse is already set, awaiting page.mouse should return that same object without calling _ensure_session."""
        # Create a minimal dummy browser session with the attributes Page expects in __init__
        class DummyBrowserSession:
            def __init__(self):
                # cdp_client is accessed in Page.__init__; it does not need to be functional for this test
                self.cdp_client = object()
                self.id = "dummy-session-id"

        browser_session = DummyBrowserSession()
        page = Page(browser_session, target_id="target-123")

        # Pre-set _mouse to a sentinel so the property returns it directly
        sentinel = object()
        page._mouse = sentinel

        # Await the async property and verify it returns the exact sentinel object
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(page.mouse)
        self.assertIs(result, sentinel)
