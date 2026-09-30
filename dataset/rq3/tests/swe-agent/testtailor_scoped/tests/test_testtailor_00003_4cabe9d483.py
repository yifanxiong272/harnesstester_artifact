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
        # Action designed to take the 'raise_function_calling' branch with an error code and message
        action = 'raise_function_calling missing "format message"'
        with self.assertRaises(FunctionCallingFormatError) as cm:
            _handle_raise_commands(action)

        exc = cm.exception
        # The exception should preserve the provided message and error_code
        self.assertEqual(exc.message, "format message")
        self.assertIn("error_code", exc.extra_info)
        self.assertEqual(exc.extra_info["error_code"], "missing")
        # The string form should include the error_code annotation added in the constructor
        self.assertIn("[error_code=missing]", str(exc))
