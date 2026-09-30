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
        """Ensure SSL_CERT_FILE takes precedence and is propagated into returned env when it exists,
        even if REQUESTS_CA_BUNDLE and GIT_SSL_CAINFO are set to different values."""
        ssl_path = "/fake/path/to/cert.pem"
        other_path = "/other/path/to/cert.pem"

        # Prepare environment with SSL_CERT_FILE and differing REQUESTS_CA_BUNDLE / GIT_SSL_CAINFO
        env_updates = {
            "SSL_CERT_FILE": ssl_path,
            "REQUESTS_CA_BUNDLE": other_path,
            "GIT_SSL_CAINFO": other_path,
        }

        # Ensure os.path.exists returns True (so the function treats the files as present)
        with unittest.mock.patch.dict(os.environ, env_updates, clear=False):
            with unittest.mock.patch("os.path.exists", return_value=True):
                returned = get_git_ssl_env()

        # The function should choose SSL_CERT_FILE and set both GIT_SSL_CAINFO and REQUESTS_CA_BUNDLE to it
        self.assertIn("GIT_SSL_CAINFO", returned)
        self.assertIn("REQUESTS_CA_BUNDLE", returned)
        self.assertEqual(returned["GIT_SSL_CAINFO"], ssl_path)
        self.assertEqual(returned["REQUESTS_CA_BUNDLE"], ssl_path)
