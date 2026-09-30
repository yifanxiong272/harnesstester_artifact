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
        """Test that check_tools removes default fields and unsupported formats for Gemini LLMs
        and does not mutate the original tools list.
        """
        # Prepare a tool with various properties to exercise removals
        tools = [
            {
                'type': 'function',
                'function': {
                    'name': 'test_tool',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'count': {'type': 'integer', 'default': 10},
                            # Unsupported string format that should be removed
                            'link': {'type': 'string', 'format': 'uri', 'default': 'http://example.com'},
                            # Supported enum format that should be preserved
                            'choice': {
                                'type': 'string',
                                'format': 'enum',
                                'default': 'a',
                                'enum': ['a', 'b'],
                            },
                            # Supported date-time format that should be preserved
                            'when': {
                                'type': 'string',
                                'format': 'date-time',
                                'default': '2020-01-01T00:00:00Z',
                            },
                        },
                        'required': ['link'],
                    },
                },
            }
        ]

        # Use an LLM config whose model name triggers the "gemini" branch
        llm_config = LLMConfig(model='Gemini-Pro', api_key='test_key')

        # Keep a deep copy of the original to assert no mutation occurs
        original_tools = copy.deepcopy(tools)

        checked_tools = check_tools(tools, llm_config)

        # The function should return a (deep)copied and modified version, not the same object
        self.assertIsNot(checked_tools, tools)
        # Original input must remain unchanged
        self.assertEqual(tools, original_tools)

        # Inspect the modified tool properties
        props = checked_tools[0]['function']['parameters']['properties']

        # All 'default' keys should be removed
        for prop in props.values():
            self.assertNotIn('default', prop)

        # 'link' had unsupported format 'uri' so its 'format' should be removed
        self.assertNotIn('format', props['link'])

        # 'choice' had supported 'enum' format and should retain it
        self.assertIn('format', props['choice'])
        self.assertEqual(props['choice']['format'], 'enum')

        # 'when' had supported 'date-time' format and should retain it
        self.assertIn('format', props['when'])
        self.assertEqual(props['when']['format'], 'date-time')
