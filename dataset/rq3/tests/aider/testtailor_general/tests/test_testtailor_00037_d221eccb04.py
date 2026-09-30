import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.exceptions')
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
        """When litellm contains an Error class not present in exception_info, _load should raise."""
        import sys
        import types
        from unittest import mock

        # Create a fake litellm module that defines a new Exception class ending with "Error"
        fake_mod = types.ModuleType("litellm")

        class InjectedError(Exception):
            pass

        fake_mod.InjectedError = InjectedError

        # Patch sys.modules so that importing litellm inside _load will get our fake module
        with mock.patch.dict(sys.modules, {"litellm": fake_mod}):
            # Instantiating LiteLLMExceptions triggers _load in __init__, which should raise
            with self.assertRaises(ValueError) as cm:
                LiteLLMExceptions()

        self.assertIn("InjectedError is in litellm but not in aider's exceptions list", str(cm.exception))
