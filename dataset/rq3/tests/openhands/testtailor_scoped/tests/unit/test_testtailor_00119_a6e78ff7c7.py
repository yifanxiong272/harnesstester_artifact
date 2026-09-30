import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.core.exceptions')
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
        """Ensure AgentNoInstructionError forwards the message to its base via super().__init__."""
        # Default message should be set when no argument is provided
        err_default = AgentNoInstructionError()
        self.assertEqual(str(err_default), "Instruction must be provided")
        self.assertEqual(err_default.args[0], "Instruction must be provided")

        # Custom message should be preserved and available via str() and args
        custom_msg = "custom instruction required"
        err_custom = AgentNoInstructionError(custom_msg)
        self.assertEqual(str(err_custom), custom_msg)
        self.assertEqual(err_custom.args[0], custom_msg)

        # When raised, the exception should carry the provided message
        with self.assertRaises(AgentNoInstructionError) as cm:
            raise AgentNoInstructionError("raised message")
        self.assertEqual(str(cm.exception), "raised message")
