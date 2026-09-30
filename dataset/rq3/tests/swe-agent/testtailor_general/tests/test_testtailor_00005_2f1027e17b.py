import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.models')
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
        """Trigger the 'raise_function_calling' branch and verify the raised exception."""
        action = "raise_function_calling missing 'format is invalid'"
        with self.assertRaises(FunctionCallingFormatError) as cm:
            _handle_raise_commands(action)
        exc = cm.exception
        # The original message (without appended error_code tag) is stored on .message
        self.assertEqual(exc.message, "format is invalid")
        # extra_info should contain the parsed error code
        self.assertIn("error_code", exc.extra_info)
        self.assertEqual(exc.extra_info["error_code"], "missing")
        # The string representation includes the appended [error_code=...]
        self.assertIn("[error_code=missing]", str(exc))
