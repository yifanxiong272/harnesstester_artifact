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
        """up_env should emit an 'update' event with the env feed and provided payload."""
        # create a mock socketio with an emit method
        socketio = Mock()

        # construct WebUpdate instance without running __init__ to avoid side effects
        web = WebUpdate.__new__(WebUpdate)
        web._socketio = socketio
        web.log_stream = None  # satisfy attribute if used elsewhere

        # call the method under test
        web.up_env("environment changed", type_="warning", format="text", thought_idx=7)

        # expected payload
        expected = {
            "feed": "env",
            "message": "environment changed",
            "format": "text",
            "thought_idx": 7,
            "type": "warning",
        }

        # assert socketio.emit was called with the correct event and payload
        socketio.emit.assert_called_once_with("update", expected)
