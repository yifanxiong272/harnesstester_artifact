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
        """Return ExInfo advising to install boto3 when APIConnectionError mentions boto3."""
        # Avoid the real _load behavior which inspects the real litellm module
        orig_load = LiteLLMExceptions._load
        LiteLLMExceptions._load = lambda self, strict=False: None

        # Obtain reference to the original __import__ in a way that works
        builtins_obj = __builtins__
        if isinstance(builtins_obj, dict):
            orig_import = builtins_obj["__import__"]
        else:
            orig_import = builtins_obj.__import__

        # Create a fake litellm module object with the APIConnectionError we need
        FakeModule = type("FakeModule", (), {})
        fake = FakeModule()

        class APIConnectionError(Exception):
            pass

        fake.APIConnectionError = APIConnectionError

        # Patch the import mechanism to return our fake module when "litellm" is imported
        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "litellm":
                return fake
            return orig_import(name, globals, locals, fromlist, level)

        if isinstance(builtins_obj, dict):
            builtins_obj["__import__"] = fake_import
        else:
            builtins_obj.__import__ = fake_import

        try:
            # Create an exception instance whose string contains 'boto3'
            ex = fake.APIConnectionError("Could not import boto3 - missing dependency boto3")

            # Instantiate LiteLLMExceptions (uses the no-op _load)
            lle = LiteLLMExceptions()
            # Ensure exceptions dict is empty so fallback doesn't interfere
            lle.exceptions = {}

            info = lle.get_ex_info(ex)

            self.assertIsInstance(info, ExInfo)
            self.assertEqual(info.name, "APIConnectionError")
            self.assertEqual(info.retry, False)
            self.assertIn("pip install boto3", info.description)
        finally:
            # Restore originals
            LiteLLMExceptions._load = orig_load
            if isinstance(builtins_obj, dict):
                builtins_obj["__import__"] = orig_import
            else:
                builtins_obj.__import__ = orig_import
