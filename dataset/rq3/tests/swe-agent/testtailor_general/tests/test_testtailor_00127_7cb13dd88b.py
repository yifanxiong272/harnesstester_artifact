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
        """Ensure a required argument after an optional one raises the expected ValueError."""
        # Create minimal argument-like objects
        class Arg:
            def __init__(self, name, required):
                self.name = name
                self.required = required

        optional_arg = Arg("opt", False)
        required_arg = Arg("req", True)

        # Construct a Command instance without running pydantic validators
        cmd = Command.construct(name="cmd", arguments=[optional_arg, required_arg])

        with self.assertRaises(ValueError) as cm:
            # Call the validator directly to trigger the specific error path
            Command.validate_arguments(cmd)

        expected = "Command 'cmd': Required argument 'req' cannot come after optional arguments"
        self.assertEqual(str(cm.exception), expected)
