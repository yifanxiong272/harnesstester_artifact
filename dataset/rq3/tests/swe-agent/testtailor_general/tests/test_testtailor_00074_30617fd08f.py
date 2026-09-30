import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.tools.tools')
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
        """Disabling the bash tool with a non-function/json parser should raise ValueError."""
        # Ensure the parser classes expose a 'type' attribute so the error message formatting won't fail.
        setattr(FunctionCallingParser, "type", "function_calling")
        setattr(JsonParser, "type", "json")

        cfg = ToolConfig()
        cfg.enable_bash_tool = False
        # Use a value that is NOT an instance of FunctionCallingParser or JsonParser
        cfg.parse_function = object()

        with self.assertRaises(ValueError) as cm:
            cfg.model_post_init(None)

        msg = str(cm.exception)
        self.assertIn("Bash tool can only be disabled", msg)
        # Ensure the message mentions the expected parser types
        self.assertIn("function_calling", msg)
        self.assertIn("json", msg)
