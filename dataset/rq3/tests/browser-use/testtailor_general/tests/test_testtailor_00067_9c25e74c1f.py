import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.browser.demo_mode')
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
        """Test DemoMode.__init__ sets up initial attributes correctly."""
        # Local imports allowed inside the test body per instructions
        import asyncio
        import logging

        # Import the target class
        from browser_use.browser.demo_mode import DemoMode

        # Create a minimal session-like stub
        class DummySession:
            pass

        session = DummySession()
        session.id = 'test-session-1234'
        # Instantiate DemoMode with the stub session
        demo = DemoMode(session)

        # Basic attribute expectations
        self.assertIs(demo.session, session)
        # Logger should be a logging.Logger and include 'DemoMode' in its name
        self.assertIsInstance(demo.logger, logging.Logger)
        self.assertIn('DemoMode', demo.logger.name)

        # Internal state initialized as expected
        self.assertIsNone(demo._script_identifier)
        self.assertIsNone(demo._script_source)
        self.assertFalse(demo._panel_ready)

        # Lock should be an asyncio.Lock and initially unlocked
        self.assertIsInstance(demo._lock, asyncio.Lock)
        self.assertFalse(demo._lock.locked())
