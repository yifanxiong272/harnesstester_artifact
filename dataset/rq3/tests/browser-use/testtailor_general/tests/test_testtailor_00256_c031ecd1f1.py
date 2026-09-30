import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.schema')
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
		"""If model.model_json_schema returns a non-dict object (but exposes .get),
		create_optimized_json_schema should raise the expected ValueError."""
		class FakeSchema:
			# Provide a get method so defs_lookup extraction works,
			# but do not make this a dict so optimize_schema returns the object unchanged.
			def get(self, key, default=None):
				if key == '$defs':
					return {}
				return default

		class FakeModel:
			@staticmethod
			def model_json_schema():
				# Return a non-dict object to trigger the "not a dictionary" branch
				return FakeSchema()

		with self.assertRaisesRegex(ValueError, r'Optimized schema result is not a dictionary'):
			SchemaOptimizer.create_optimized_json_schema(FakeModel)
