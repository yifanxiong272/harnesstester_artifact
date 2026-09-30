import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.agenthub.loc_agent.function_calling')
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
        """Test that a ModelResponse with a tool call and assistant message content
        is converted into an IPythonRunCellAction with correct metadata."""
        # Build the response as an actual ModelResponse instance so ToolCallMetadata validation succeeds.
        # Get the ModelResponse type from ToolCallMetadata's model field annotation
        MR_cls = ToolCallMetadata.model_fields['model_response'].annotation

        # Construct a plain dict that matches the expected shape for ModelResponse so we can validate/create one
        response_data = {
            'id': 'response-xyz',
            'choices': [
                {
                    'message': {
                        # Provide content so the code path sets `thought = ''` then updates it from content
                        'content': 'Thinking about searching code...',
                        # Provide a non-empty tool_calls list to trigger the tool-calling branch
                        'tool_calls': [
                            {
                                'id': 'tool-call-123',
                                'function': {
                                    'name': 'search_code_snippets',
                                    # arguments must be a JSON string per the implementation
                                    'arguments': '{"query": "foo"}'
                                }
                            }
                        ]
                    }
                }
            ]
        }

        # Create a validated ModelResponse instance (pydantic v2 API)
        response = MR_cls.model_validate(response_data)

        # Execute the function under test
        actions = response_to_actions(response)

        # Assertions
        self.assertIsInstance(actions, list)
        self.assertEqual(len(actions), 1)

        action = actions[0]
        # For the ALL_FUNCTIONS branch an IPythonRunCellAction with a .code attribute is expected
        self.assertTrue(hasattr(action, 'code'))
        self.assertIn('search_code_snippets', action.code)
        # Response id should be propagated to the action
        self.assertEqual(action.response_id, 'response-xyz')
        # Tool call metadata should be attached and reflect the tool call
        self.assertTrue(hasattr(action, 'tool_call_metadata'))
        self.assertEqual(action.tool_call_metadata.function_name, 'search_code_snippets')
        self.assertEqual(action.tool_call_metadata.tool_call_id, 'tool-call-123')
        self.assertEqual(action.tool_call_metadata.total_calls_in_response, 1)
