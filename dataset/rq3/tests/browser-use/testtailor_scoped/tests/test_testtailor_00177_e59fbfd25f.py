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
        """Ensure _get_client reads credentials from environment when instance attributes are None."""
        # Prepare environment variables that _get_client should read
        creds = {
            'AWS_ACCESS_KEY_ID': 'TEST_AK',
            'AWS_SECRET_ACCESS_KEY': 'TEST_SK',
            'AWS_SESSION_TOKEN': 'TEST_ST',
            'AWS_REGION': 'us-west-2',
        }

        # Create a fake boto3 module with a client function to avoid importing the real boto3
        fake_boto3 = Mock()
        fake_boto3.client = Mock(return_value='mock-bedrock-client')

        # Patch environment and inject the fake boto3 module into sys.modules so "from boto3 import client" works
        with patch.dict('os.environ', creds):
            with patch.dict('sys.modules', {'boto3': fake_boto3}):
                # Create the model instance with no explicit credentials so getenv is used
                model = ChatAWSBedrock()
                model.aws_access_key_id = None
                model.aws_secret_access_key = None
                model.aws_session_token = None
                model.aws_region = None
                model.aws_sso_auth = False
                model.session = None

                client = model._get_client()

                # Assert boto3.client (our fake) was called with credentials from environment and correct service/region
                fake_boto3.client.assert_called_once_with(
                    service_name='bedrock-runtime',
                    region_name='us-west-2',
                    aws_access_key_id='TEST_AK',
                    aws_secret_access_key='TEST_SK',
                    aws_session_token='TEST_ST',
                )
                self.assertEqual(client, 'mock-bedrock-client')
