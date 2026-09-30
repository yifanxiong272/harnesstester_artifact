import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.tools.registry.service')
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
        """When the action's param_model raises, execute_action should surface the validation error (wrapped)."""
        registry = Registry()

        action_name = 'failing_action'

        # Create a param_model callable that raises an error when invoked to simulate invalid params
        def bad_param_model(**kwargs):
            raise TypeError('simulated param model failure')

        # Minimal action object with the attributes execute_action expects
        action_obj = type('ActionObj', (), {})()
        action_obj.param_model = bad_param_model
        action_obj.function = lambda **kwargs: None  # won't be reached

        # Inject the fake action into the internal registry
        registry.registry.actions[action_name] = action_obj

        params = {'foo': 'bar'}

        with self.assertRaises(RuntimeError) as cm:
            asyncio.run(registry.execute_action(action_name, params))

        err_msg = str(cm.exception)
        # The inner exception message should be preserved and wrapped by execute_action
        self.assertIn('Invalid parameters', err_msg)
        self.assertIn(str(params), err_msg)
        self.assertIn(action_name, err_msg)
        self.assertIn('TypeError', err_msg)
