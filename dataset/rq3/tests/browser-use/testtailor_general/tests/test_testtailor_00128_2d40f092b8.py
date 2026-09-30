import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.mistral.schema')
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
    def test_strip_unsupported_keywords_removes_keys(self):
        """Mistral-compatible schema builder should remove unsupported validation keywords."""

        # Create a fake model with a model_json_schema method returning a schema
        class FakeModel:
            @staticmethod
            def model_json_schema():
                return {
                    "type": "object",
                    "title": "Fake",
                    "description": "A fake model for testing",
                    "properties": {
                        "name": {
                            "type": "string",
                            "minLength": 2,
                            "maxLength": 10,
                            "pattern": "^[A-Z].*",
                            "format": "email",
                            "description": "A name field",
                        },
                        "nested": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "format": "uuid",
                                }
                            },
                        },
                    },
                }

        # Build the mistral-compatible schema
        mistral_schema = MistralSchemaOptimizer.create_mistral_compatible_schema(FakeModel)

        # Helper to find any unsupported keywords anywhere in the schema structure
        def find_unsupported_keys(obj):
            found = set()
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in MistralSchemaOptimizer.UNSUPPORTED_KEYWORDS:
                        found.add(k)
                    found.update(find_unsupported_keys(v))
            elif isinstance(obj, list):
                for item in obj:
                    found.update(find_unsupported_keys(item))
            return found

        unsupported_found = find_unsupported_keys(mistral_schema)

        # Assert no unsupported keywords are present
        self.assertEqual(unsupported_found, set(), f"Unsupported keys present: {unsupported_found}")

        # Also assert that expected structural pieces remain intact
        self.assertIsInstance(mistral_schema, dict)
        self.assertIn("properties", mistral_schema)
        self.assertIn("name", mistral_schema["properties"])
        # The 'type' for the name property should still be present and set to string
        self.assertEqual(mistral_schema["properties"]["name"].get("type"), "string")
        # Ensure additionalProperties was added for objects (SchemaOptimizer enforces this)
        self.assertTrue(
            mistral_schema.get("additionalProperties", True) is False
            or mistral_schema["properties"]["nested"].get("additionalProperties", True) is False
        )
