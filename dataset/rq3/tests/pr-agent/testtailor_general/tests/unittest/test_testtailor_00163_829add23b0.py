import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.codecommit_client')
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
        # Ensure that when boto3.client raises an exception, _connect_boto_client wraps it in ValueError
        with patch("pr_agent.git_providers.codecommit_client.boto3.client", side_effect=Exception("no creds")):
            client = CodeCommitClient()
            with self.assertRaisesRegex(ValueError, r"Failed to connect to AWS CodeCommit: no creds"):
                client._connect_boto_client()
