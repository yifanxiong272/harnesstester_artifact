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
        """Invoke the async handler with a prefixed JSON string and verify printed output."""
        sample = {"rating": 5, "comment": "Great"}
        payload = "human_feedback" + json.dumps(sample)

        # Patch builtins.print to capture print calls without needing io or contextlib
        with unittest.mock.patch("builtins.print") as mock_print:
            asyncio.run(handle_human_feedback(payload))

        expected = f"Received human feedback: {sample}"
        self.assertTrue(mock_print.called)
        mock_print.assert_any_call(expected)
