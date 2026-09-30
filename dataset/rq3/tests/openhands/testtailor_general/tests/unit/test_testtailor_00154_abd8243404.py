import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.llm.llm_utils')
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
        """Ensure check_tools strips default fields and unsupported formats for Gemini models
        and does not mutate the input tools list.
        """
        # Prepare input tools with various properties:
        # - param1: string with unsupported format 'binary' and a default -> both should be removed in checked result
        # - param2: string with supported format 'enum' and a default -> default removed, format kept
        # - param3: number with default -> default removed
        tools = [
            {
                'type': 'function',
                'function': {
                    'name': 'test_tool',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'param1': {'type': 'string', 'format': 'binary', 'default': 'd1'},
                            'param2': {'type': 'string', 'format': 'enum', 'default': 'd2'},
                            'param3': {'type': 'number', 'default': 42},
                        },
                    },
                },
            }
        ]

        # Use a Gemini model name to trigger the special branch
        llm_config = LLMConfig(model='Gemini-Preview-123', api_key='fake_key')

        # Run the function under test
        checked_tools = check_tools(tools, llm_config)

        # Ensure we returned the same number of tools
        self.assertEqual(len(checked_tools), len(tools))

        # Original tools must not be mutated
        orig_props = tools[0]['function']['parameters']['properties']
        self.assertIn('default', orig_props['param1'])
        self.assertIn('format', orig_props['param1'])
        self.assertIn('default', orig_props['param2'])
        self.assertIn('format', orig_props['param2'])
        self.assertIn('default', orig_props['param3'])

        # Checked tools should have had defaults removed for all properties
        checked_props = checked_tools[0]['function']['parameters']['properties']
        self.assertNotIn('default', checked_props['param1'])
        self.assertNotIn('default', checked_props['param2'])
        self.assertNotIn('default', checked_props['param3'])

        # Unsupported string format should be removed ('binary' removed)
        self.assertNotIn('format', checked_props['param1'])

        # Supported string format 'enum' should be preserved
        self.assertIn('format', checked_props['param2'])
        self.assertEqual(checked_props['param2']['format'], 'enum')
