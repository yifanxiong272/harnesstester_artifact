import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.llm.fn_call_converter')
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
        """Ensure get_example_for_tools recognizes the LLM-based edit tool named 'edit_file'."""
        tools = [
            {
                'type': 'function',
                'function': {
                    'name': 'edit_file',
                    'description': 'LLM-based file edit tool used by the agent.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'path': {'type': 'string', 'description': 'File path'},
                            'content': {'type': 'string', 'description': 'Content to write'},
                        },
                        'required': ['path', 'content'],
                    },
                },
            }
        ]

        example = get_example_for_tools(tools)

        # Basic structure checks
        self.assertTrue(
            example.startswith("Here's a running example of how to perform a task with the provided tools.")
        )
        self.assertIn(
            'USER: Create a list of numbers from 1 to 10, and display them in a web page at port 5000.',
            example,
        )

        # Should include the LLM-based edit_file examples
        self.assertIn(TOOL_EXAMPLES['edit_file']['create_file'], example)
        self.assertIn(TOOL_EXAMPLES['edit_file']['edit_file'], example)

        # Should NOT include examples for other tools that would have been added for different names
        self.assertNotIn(TOOL_EXAMPLES['execute_bash']['check_dir'], example)
        self.assertNotIn(TOOL_EXAMPLES['str_replace_editor']['create_file'], example)
        self.assertNotIn(TOOL_EXAMPLES['browser']['view_page'], example)
        self.assertNotIn(TOOL_EXAMPLES['finish']['example'], example)
