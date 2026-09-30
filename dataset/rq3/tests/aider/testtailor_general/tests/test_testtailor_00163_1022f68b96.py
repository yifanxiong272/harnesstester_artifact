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
        """Insufficient credits APIError should return the specific non-retryable ExInfo."""
        # Create a fake litellm module object with the required exception classes
        class FakeModule:
            pass

        fake = FakeModule()

        class APIError(Exception):
            pass

        class APIConnectionError(Exception):
            pass

        fake.APIError = APIError
        fake.APIConnectionError = APIConnectionError

        # Patch the import mechanism so that "import litellm" returns our fake module.
        builtins_obj = __builtins__
        if isinstance(builtins_obj, dict):
            orig_import = builtins_obj.get("__import__")
        else:
            orig_import = builtins_obj.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "litellm":
                return fake
            return orig_import(name, globals, locals, fromlist, level)

        try:
            if isinstance(builtins_obj, dict):
                builtins_obj["__import__"] = fake_import
            else:
                builtins_obj.__import__ = fake_import

            # Create a LiteLLMExceptions instance without triggering _load
            lle = LiteLLMExceptions.__new__(LiteLLMExceptions)
            lle.exceptions = {}

            # Exception message must contain both "insufficient credits" and '"code":402'
            ex = fake.APIError('Insufficient credits "code":402')
            info = lle.get_ex_info(ex)

            self.assertIsInstance(info, ExInfo)
            self.assertEqual(info.name, "APIError")
            self.assertFalse(info.retry)
            self.assertEqual(
                info.description,
                "Insufficient credits with the API provider. Please add credits.",
            )
        finally:
            # Restore original import
            if isinstance(builtins_obj, dict):
                builtins_obj["__import__"] = orig_import
            else:
                builtins_obj.__import__ = orig_import
