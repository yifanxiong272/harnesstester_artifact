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
        """When a per-version environment variable is set, _base_url returns it directly."""
        env_key = 'BROWSER_USE_CLOUD_BASE_URL_V2'
        env_value = 'https://per-version.example/path'
        # Preserve previous environment state
        prev = os.environ.get(env_key)
        os.environ[env_key] = env_value
        try:
            # Use a lower-case version to ensure version.upper() is used inside the function
            result = _base_url('v2')
            self.assertEqual(result, env_value)
        finally:
            # Restore environment
            if prev is None:
                del os.environ[env_key]
            else:
                os.environ[env_key] = prev
