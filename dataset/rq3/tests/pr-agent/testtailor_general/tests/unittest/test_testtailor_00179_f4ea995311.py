import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.secret_providers.google_cloud_storage_secret_provider')
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
        """Ensure that when upload_from_string raises, the error is logged and the exception is re-raised."""
        secret_name = "my-secret"
        secret_value = "super-secret-value"

        # Create an instance without running __init__
        provider = object.__new__(GoogleCloudStorageSecretProvider)

        # Prepare bucket/blob mocks such that upload_from_string raises
        mock_blob = MagicMock()
        mock_blob.upload_from_string.side_effect = Exception("upload failed")
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        provider.bucket = mock_bucket

        # Patch get_logger to capture logged error
        with patch('pr_agent.secret_providers.google_cloud_storage_secret_provider.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            with self.assertRaises(Exception) as cm:
                provider.store_secret(secret_name, secret_value)

            # Exception propagated and contains our message
            self.assertIn("upload failed", str(cm.exception))

            # Logger.error was called and message includes secret name
            mock_logger.error.assert_called_once()
            logged_msg = mock_logger.error.call_args[0][0]
            self.assertIn(secret_name, logged_msg)

            # Ensure blob was retrieved and upload attempted with the correct value
            mock_bucket.blob.assert_called_once_with(secret_name)
            mock_blob.upload_from_string.assert_called_once_with(secret_value)
