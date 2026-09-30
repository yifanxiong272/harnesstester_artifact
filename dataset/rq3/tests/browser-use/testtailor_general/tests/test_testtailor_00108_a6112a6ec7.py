import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.skill_cli.profile_use')
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
    def test_download_raises_when_curl_missing(self):
        """download_profile_use should raise a RuntimeError if curl is not available."""
        with unittest.mock.patch('shutil.which', return_value=None):
            with self.assertRaisesRegex(RuntimeError, r'curl is required to download profile-use'):
                download_profile_use()
