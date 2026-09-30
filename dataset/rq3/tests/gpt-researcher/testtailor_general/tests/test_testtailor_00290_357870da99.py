import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('backend.server.server_utils')
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
        """Call handle_human_feedback with a valid prefixed JSON string and assert printed output."""
        payload = {"rating": 5, "comment": "Great"}
        data = "human_feedback" + json.dumps(payload)
        with unittest.mock.patch('builtins.print') as mock_print:
            asyncio.get_event_loop().run_until_complete(handle_human_feedback(data))
            mock_print.assert_called_with(f"Received human feedback: {payload}")
