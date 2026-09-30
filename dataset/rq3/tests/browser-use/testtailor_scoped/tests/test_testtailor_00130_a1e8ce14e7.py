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
		"""Verify _create_param_model builds a Pydantic model from a function signature,
		excluding special parameters defined in SpecialActionParameters.
		"""
		# Create a registry instance
		reg = Registry()

		# Define a sample function that mixes normal params and special params by name.
		# We intentionally do not import BrowserSession here; only the parameter names matter
		# for exclusion of special parameters.
		def sample_action(text: str, count: int = 3, browser_session=None, page_url=None):
			# body not used for model creation
			return f'{text}:{count}'

		# Create the param model for the function
		model_type = reg._create_param_model(sample_action)

		# The returned model should be a subclass of ActionModel (pydantic BaseModel)
		self.assertTrue(issubclass(model_type, ActionModel))

		# Ensure normal parameters are present in the model fields
		model_fields = set(model_type.model_fields.keys())
		self.assertIn('text', model_fields)
		self.assertIn('count', model_fields)

		# Ensure special parameters are excluded
		self.assertNotIn('browser_session', model_fields)
		self.assertNotIn('page_url', model_fields)

		# Validate instantiation with required/optional parameters
		instance = model_type(text='hello', count=7)
		# Attribute access should work and values preserved
		self.assertEqual(getattr(instance, 'text'), 'hello')
		self.assertEqual(getattr(instance, 'count'), 7)

		# If optional param is omitted, default should apply
		instance_default = model_type(text='hi')
		self.assertEqual(getattr(instance_default, 'count'), 3)

		# Missing required parameter should raise an error on construction
		with self.assertRaises(Exception):
			# omit required 'text'
			model_type(count=1)
