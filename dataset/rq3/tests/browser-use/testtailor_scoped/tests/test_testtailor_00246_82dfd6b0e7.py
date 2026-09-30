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
        """Ensure SchemaOptimizer removes 'default' keys from the schema for fields
        when remove_defaults=True. This targets the branch where the optimizer
        encounters a dict key 'default' and skips it (continue).
        """
        class DefaultModel(BaseModel):
            required_field: str
            with_default: int = 7

        # Get the raw JSON schema produced by pydantic and ensure the field has a default initially
        raw_schema = DefaultModel.model_json_schema()
        props = raw_schema.get('properties', {})
        assert 'with_default' in props, "Precondition failed: expected 'with_default' property in raw schema."
        assert 'default' in props['with_default'], "Precondition failed: raw schema should contain 'default' for the field with a default."

        # Run the optimizer asking it to remove defaults
        optimized = SchemaOptimizer.create_optimized_json_schema(DefaultModel, remove_defaults=True)

        # The 'default' key for our specific field should have been removed
        optimized_props = optimized.get('properties', {})
        self.assertIn('with_default', optimized_props, "Optimized schema missing the 'with_default' property.")
        self.assertNotIn('default', optimized_props['with_default'], "Optimizer did not remove the 'default' key for the field as expected.")
