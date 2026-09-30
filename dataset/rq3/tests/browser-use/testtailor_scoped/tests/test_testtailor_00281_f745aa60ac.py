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
        """Ensure ModelProviderError is raised when no AWS credentials are provided and not using SSO."""
        # Ensure a boto3.client can be imported inside the method, even if boto3 isn't installed in the test env
        sys = __import__('sys')
        types = __import__('types')
        fake_boto3 = types.ModuleType('boto3')

        def fake_client(*args, **kwargs):
            class DummyClient:
                pass
            return DummyClient()

        fake_boto3.client = fake_client
        original_boto3 = sys.modules.get('boto3')
        sys.modules['boto3'] = fake_boto3

        # Clear relevant AWS env vars to simulate missing credentials
        os = __import__('os')
        env_keys = ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'AWS_REGION', 'AWS_DEFAULT_REGION')
        backups = {k: os.environ.get(k) for k in env_keys}
        for k in env_keys:
            os.environ.pop(k, None)

        try:
            # Create model instance with no credentials and no session and not using SSO
            model = ChatAWSBedrock()
            model.aws_access_key_id = None
            model.aws_secret_access_key = None
            model.aws_session_token = None
            model.aws_region = None
            model.aws_sso_auth = False
            model.session = None

            with self.assertRaises(ModelProviderError) as cm:
                model._get_client()

            err = cm.exception
            # Validate error message and that the model name is set on the exception
            self.assertIn('AWS credentials not found', err.message)
            self.assertEqual(err.model, model.name)
        finally:
            # Restore sys.modules
            if original_boto3 is None:
                del sys.modules['boto3']
            else:
                sys.modules['boto3'] = original_boto3
            # Restore environment variables
            for k, v in backups.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
