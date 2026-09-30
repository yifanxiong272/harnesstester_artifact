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
        """Ensure that when the model erroneously includes the command end_name
        as an argument it is ignored (extra_args.discard(command.end_name) branch).
        """
        parser = FunctionCallingParser()

        # Create a multi-line command that uses an end marker "END"
        cmd = Command(
            name="multi",
            docstring="multi-line command",
            end_name="END",
            arguments=[
                {
                    "name": "content",
                    "description": "the content for the multi-line command",
                    "type": "string",
                    "required": True,
                    "argument_format": "{{ value }}",
                }
            ],
        )

        # Simulate a tool call where the model included the end_name as an (unexpected) argument.
        # Provide arguments as a JSON string so the parser goes through the json.loads branch and
        # sets the local 'values' variable (avoiding the unbound local issue).
        tool_call = {
            "function": {
                "name": "multi",
                "arguments": '{"content": "hello", "END": ""}',
            }
        }

        action = parser._parse_tool_call(tool_call, [cmd])
        # invoke_format defaults to "multi {content} " -> stripped => "multi hello"
        self.assertEqual(action, "multi hello")
