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
        """When aws_sso_auth is True, _get_client should call boto3.client with only service_name and region_name."""
        captured = {}

        def fake_client(*args, **kwargs):
            captured['args'] = args
            captured['kwargs'] = kwargs
            return 'FAKE_BOTO3_CLIENT'

        FakeModule = type('FakeModule', (), {})
        fake_module = FakeModule()
        fake_module.client = fake_client

        # Patch the import system to return our fake module when boto3 is requested
        builtins_obj = __builtins__ if isinstance(__builtins__, dict) else __builtins__
        if isinstance(__builtins__, dict):
            orig_import = builtins_obj.get('__import__')
        else:
            orig_import = builtins_obj.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == 'boto3':
                return fake_module
            return orig_import(name, globals, locals, fromlist, level)

        try:
            if isinstance(__builtins__, dict):
                __builtins__['__import__'] = fake_import
            else:
                __builtins__.__import__ = fake_import

            model = ChatAWSBedrock()
            model.aws_sso_auth = True
            model.aws_region = 'eu-central-1'

            client = model._get_client()

            self.assertEqual(client, 'FAKE_BOTO3_CLIENT')
            self.assertIn('kwargs', captured)
            self.assertEqual(
                captured['kwargs'],
                {'service_name': 'bedrock-runtime', 'region_name': 'eu-central-1'}
            )
            self.assertEqual(captured.get('args', ()), ())
        finally:
            # Restore original import
            if isinstance(__builtins__, dict):
                if orig_import is None:
                    del __builtins__['__import__']
                else:
                    __builtins__['__import__'] = orig_import
            else:
                __builtins__.__import__ = orig_import
