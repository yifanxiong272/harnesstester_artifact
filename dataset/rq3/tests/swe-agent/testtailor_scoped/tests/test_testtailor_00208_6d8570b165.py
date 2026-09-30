import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.tools.parsing')
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
        """When a required argument is not provided in the tool call, the parser should raise a missing_arg error."""
        parser = FunctionCallingParser()

        # Minimal stand-ins for Argument and Command-like objects expected by the parser
        class SimpleArg:
            def __init__(self, name: str, required: bool):
                self.name = name
                self.required = required
                self.argument_format = "{{value}}"

        class SimpleCommand:
            def __init__(self, name: str, arguments):
                self.name = name
                self.arguments = arguments
                self.end_name = None
                # invoke_format must be a string that can be formatted with argument names
                self.invoke_format = f"{name} " + " ".join(f"{{{a.name}}}" for a in arguments)

        # Create a command that requires a "path" argument
        cmd = SimpleCommand("mycmd", [SimpleArg("path", True)])

        # Simulate a model tool call that omits the required "path" argument
        tool_call = {"function": {"name": "mycmd", "arguments": "{}"}}

        with self.assertRaises(FunctionCallingFormatError) as cm:
            parser._parse_tool_call(tool_call, [cmd])

        exc = cm.exception
        # The stored message (exc.message) should indicate the missing argument
        self.assertIn("Required argument(s) missing: path", exc.message)
        # And the error code should be "missing_arg"
        self.assertEqual(exc.extra_info.get("error_code"), "missing_arg")
