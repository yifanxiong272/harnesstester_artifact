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
    def test_remove_min_items_skips_minItems_key(self):
        """Optimizer should skip and remove 'minItems' when remove_min_items is enabled."""
        # Import pydantic and SchemaOptimizer dynamically to avoid top-level imports in this snippet.
        pyd = __import__('pydantic')
        BaseModel = getattr(pyd, 'BaseModel')
        Field = getattr(pyd, 'Field')

        schema_mod = __import__('browser_use.llm.schema', fromlist=['SchemaOptimizer'])
        SchemaOptimizer = schema_mod.SchemaOptimizer

        class ArrayModel(BaseModel):
            # This field creates a JSON Schema fragment that includes 'minItems'.
            items: list[int] = Field(..., min_items=2)

        # Request the optimizer to remove minItems entries.
        optimized_schema = SchemaOptimizer.create_optimized_json_schema(ArrayModel, remove_min_items=True)

        # Locate the schema for the 'items' property.
        items_schema = optimized_schema.get('properties', {}).get('items', {})

        # The optimizer should have removed both 'minItems' and any snake_case variant.
        self.assertNotIn('minItems', items_schema, "'minItems' should have been skipped/removed by the optimizer")
        self.assertNotIn('min_items', items_schema, "'min_items' should not appear in the optimized schema")
