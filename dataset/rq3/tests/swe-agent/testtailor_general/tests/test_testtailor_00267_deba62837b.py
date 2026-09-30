import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.api.hooks')
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
        """Verify up_banner calls socketio.emit with correct event and payload"""
        calls = []

        class DummySocketIO:
            def emit(self, event, data):
                calls.append((event, data))

        socketio = DummySocketIO()
        web_update = WebUpdate(socketio)

        msg = "Important banner message"
        web_update.up_banner(msg)

        # One call should have been made
        self.assertEqual(len(calls), 1)
        event, data = calls[0]

        # Validate event name and payload
        self.assertEqual(event, "update_banner")
        self.assertEqual(data, {"message": msg})
