import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.sync.service')
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
        """When cloud sync is disabled, handle_event should return immediately and not modify session state."""
        # Create CloudSync and force it to be disabled
        cs = CloudSync()
        cs.enabled = False

        # Create a minimal fake event
        evt = type('DummyEvent', (), {})()
        evt.event_type = 'CreateAgentSessionEvent'
        evt.id = 'session-123'

        import asyncio

        # Should run without raising and should not set session_id or auth flow flags
        asyncio.run(cs.handle_event(evt))

        self.assertIsNone(cs.session_id)
        self.assertFalse(cs.auth_flow_active)
