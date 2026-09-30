import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.tools.registry.views')
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
        """Ensure prompt_description includes parameter types and descriptions when present."""
        class DummyParamModel(BaseModel):
            @staticmethod
            def model_json_schema():
                return {
                    "properties": {
                        "url": {"type": "string", "description": "Target URL"},
                        "count": {"type": "integer"},
                    }
                }

        action = RegisteredAction(
            name="test",
            description="Do stuff",
            function=lambda *args, **kwargs: None,
            param_model=DummyParamModel,
        )

        result = action.prompt_description()
        expected = "test: Do stuff. (url=string (Target URL), count=integer)"
        self.assertEqual(result, expected)
