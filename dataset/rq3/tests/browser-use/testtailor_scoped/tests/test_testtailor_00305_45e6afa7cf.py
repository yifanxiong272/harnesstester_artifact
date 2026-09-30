import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.views')
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
        """Ensure type_with_custom_actions_no_thinking removes the thinking property from the JSON schema."""
        # Import here to comply with the instruction to only include the test class in the submission body.
        from browser_use.agent.service import AgentOutput
        from browser_use.tools.registry.views import ActionModel

        # Sanity check: base AgentOutput schema contains 'thinking'
        base_schema = AgentOutput.model_json_schema()
        self.assertIn('thinking', base_schema.get('properties', {}))

        # Create the specialized model with no thinking field
        model_cls = AgentOutput.type_with_custom_actions_no_thinking(ActionModel)

        # Retrieve the JSON schema from the generated model class
        schema = model_cls.model_json_schema()

        # Assert 'thinking' has been removed and required fields are as expected
        self.assertNotIn('thinking', schema.get('properties', {}))
        self.assertEqual(
            schema.get('required'),
            ['evaluation_previous_goal', 'memory', 'next_goal', 'action'],
        )
