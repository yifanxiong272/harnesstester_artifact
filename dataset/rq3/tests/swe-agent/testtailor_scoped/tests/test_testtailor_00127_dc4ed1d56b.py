import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.tools.utils')
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
        """Ensure get_signature handles commands with end_name and a final dict argument."""
        class Arg:
            def __init__(self, name, required):
                self.name = name
                self.required = required

        class Cmd:
            def __init__(self, name, arguments, end_name):
                self.name = name
                self.arguments = arguments
                self.end_name = end_name

        # First element is an object with .name and .required, last element is a dict
        cmd = Cmd(
            name="mycmd",
            arguments=[Arg("first", True), {"trailer": "meta"}],
            end_name="END_MARKER",
        )

        result = get_signature(cmd)
        expected = "mycmd <first>\ntrailer\nEND_MARKER"
        self.assertEqual(result, expected)
