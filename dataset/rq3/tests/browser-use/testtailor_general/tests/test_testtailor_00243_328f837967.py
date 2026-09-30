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
        """Ensure prompt_description includes parameter names, types and descriptions when properties exist."""
        # Use the project's BaseModel (imported at module level in the test suite)
        class Params(BaseModel):
            url: str
            count: int

        # Override the generated schema to ensure 'properties' include types and description
        Params.model_json_schema = staticmethod(
            lambda: {
                "title": "Params",
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "target url"},
                    "count": {"type": "integer"},
                },
            }
        )

        action = RegisteredAction(
            name="test_action",
            description="Does something",
            function=lambda *args, **kwargs: None,
            param_model=Params,
        )

        desc = action.prompt_description()

        expected = "test_action: Does something. (url=string (target url), count=integer)"
        self.assertEqual(desc, expected)
