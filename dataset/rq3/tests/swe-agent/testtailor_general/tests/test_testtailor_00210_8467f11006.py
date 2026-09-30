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
        """Creating a Command with an argument name that doesn't match the allowed pattern
        should raise a ValueError pointing out the invalid argument name.
        """
        bad_arg = {
            "name": "1bad",  # invalid: starts with a digit
            "required": True,
            "type": "string",  # provide required fields for Argument model
            "description": "an invalid name starting with a digit",
        }
        # Expect a ValueError complaining about the invalid argument name
        with self.assertRaisesRegex(ValueError, "Command 'testcmd': Invalid argument name: '1bad'"):
            Command(name="testcmd", docstring=None, signature=None, arguments=[bad_arg])
