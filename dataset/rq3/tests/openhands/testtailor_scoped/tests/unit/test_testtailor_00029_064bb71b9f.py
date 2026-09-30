import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.base')
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
        """Ensure environment variables with SANDBOX_ENV_ prefix are exposed without the prefix."""
        # Preserve original environment and restore after test
        original_environ = dict(os.environ)
        try:
            # Start from a clean environment to control test inputs
            os.environ.clear()
            # Keys that should be picked up (prefix removed)
            os.environ['SANDBOX_ENV_FOO'] = 'bar'
            os.environ['SANDBOX_ENV_EMPTY'] = ''
            # A key that should be ignored
            os.environ['UNRELATED'] = 'ignore-me'

            # Minimal sandbox config object with enable_auto_lint disabled
            class DummyConfig:
                enable_auto_lint = False

            result = _default_env_vars(DummyConfig())

            # The prefixed keys should appear without the prefix
            self.assertIn('FOO', result)
            self.assertEqual(result['FOO'], 'bar')
            self.assertIn('EMPTY', result)
            self.assertEqual(result['EMPTY'], '')
            # Unrelated keys must not be present
            self.assertNotIn('UNRELATED', result)
            # ENABLE_AUTO_LINT should not be set when config.disable_auto_lint (False)
            self.assertNotIn('ENABLE_AUTO_LINT', result)
        finally:
            os.environ.clear()
            os.environ.update(original_environ)
