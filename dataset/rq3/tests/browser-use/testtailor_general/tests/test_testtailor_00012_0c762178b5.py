import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.skill_cli.commands.cloud')
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
        """Verify that _get_base() prefers the environment variable and strips trailing slashes,
        and falls back to the default when the env var is not set."""
        # Preserve original environment value to restore later
        original = os.environ.get('BROWSER_USE_CLOUD_BASE_URL', None)
        try:
            # Case 1: environment variable is set and has a trailing slash -> should be stripped
            os.environ['BROWSER_USE_CLOUD_BASE_URL'] = 'https://custom.example/path/'
            result = _get_base()
            self.assertEqual(result, 'https://custom.example/path')

            # Case 2: environment variable removed -> should return the default base URL
            os.environ.pop('BROWSER_USE_CLOUD_BASE_URL', None)
            result_default = _get_base()
            self.assertEqual(result_default, _DEFAULT_BASE_URL)
        finally:
            # Restore original environment state
            if original is None:
                os.environ.pop('BROWSER_USE_CLOUD_BASE_URL', None)
            else:
                os.environ['BROWSER_USE_CLOUD_BASE_URL'] = original
