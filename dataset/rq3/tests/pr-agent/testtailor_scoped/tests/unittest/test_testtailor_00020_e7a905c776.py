import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.git_provider')
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
        """Verify that SSL_CERT_FILE takes precedence and overrides other cert env vars when the file exists."""
        # Use os.devnull as a path that is guaranteed to exist on the platform
        path_ssl_cert = os.devnull
        # A different (likely non-existent) path to simulate a mismatch
        path_requests = path_ssl_cert + "_different"

        # Backup original environment variables so we can restore them
        backup = {
            "SSL_CERT_FILE": os.environ.get("SSL_CERT_FILE"),
            "REQUESTS_CA_BUNDLE": os.environ.get("REQUESTS_CA_BUNDLE"),
            "GIT_SSL_CAINFO": os.environ.get("GIT_SSL_CAINFO"),
        }

        try:
            # Set environment to have SSL_CERT_FILE and a different REQUESTS_CA_BUNDLE
            os.environ["SSL_CERT_FILE"] = path_ssl_cert
            os.environ["REQUESTS_CA_BUNDLE"] = path_requests
            # Ensure GIT_SSL_CAINFO is not set so only the two above matter
            os.environ.pop("GIT_SSL_CAINFO", None)

            returned = get_git_ssl_env()

            # SSL_CERT_FILE should be chosen and both GIT_SSL_CAINFO and REQUESTS_CA_BUNDLE
            # in the returned env should be set to the SSL_CERT_FILE path.
            self.assertEqual(returned.get("GIT_SSL_CAINFO"), path_ssl_cert)
            self.assertEqual(returned.get("REQUESTS_CA_BUNDLE"), path_ssl_cert)

        finally:
            # Restore environment
            for k, v in backup.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
