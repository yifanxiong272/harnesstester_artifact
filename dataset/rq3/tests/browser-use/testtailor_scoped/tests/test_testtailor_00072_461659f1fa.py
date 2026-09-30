import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.aws.chat_bedrock')
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
        """Ensure missing boto3 raises the expected ImportError with install hint."""
        aws_model = ChatAWSBedrock()

        # Grab the real __import__ and replace it with one that raises ImportError for boto3
        if isinstance(__builtins__, dict):
            real_import = __builtins__['__import__']
        else:
            real_import = __builtins__.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            # Simulate boto3 not being installed
            if name == 'boto3' or name.startswith('boto3.'):
                raise ImportError("No module named 'boto3'")
            return real_import(name, globals, locals, fromlist, level)

        # Patch in our fake importer
        if isinstance(__builtins__, dict):
            __builtins__['__import__'] = fake_import
        else:
            __builtins__.__import__ = fake_import

        try:
            with self.assertRaisesRegex(
                ImportError,
                r"pip install browser-use\[aws\] or pip install browser-use\[all\]"
            ):
                aws_model._get_client()
        finally:
            # Restore the original importer
            if isinstance(__builtins__, dict):
                __builtins__['__import__'] = real_import
            else:
                __builtins__.__import__ = real_import
