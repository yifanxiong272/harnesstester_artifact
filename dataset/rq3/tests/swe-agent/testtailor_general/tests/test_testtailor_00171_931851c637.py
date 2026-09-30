import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.tools.commands')
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
        """Command.validate_arguments should raise on duplicate argument names when the same Argument object is used twice."""
        cmd_name = "dup_cmd"
        # Create a single Argument instance and include it twice in the arguments list
        arg = Argument(name="arg1", required=True, type="string", description="first")
        with self.assertRaises(ValueError) as cm:
            # Passing the same Argument instance twice should trigger the duplicate-detection logic
            Command(name=cmd_name, docstring=None, arguments=[arg, arg])
        msg = str(cm.exception)
        # Check message mentions duplicate argument names and includes the offending name
        self.assertIn(f"Command '{cmd_name}': Duplicate argument names:", msg)
        self.assertIn("{'arg1'}", msg)
