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
        """Ensure SANDBOX_ENV_* variables are propagated and ENABLE_AUTO_LINT is set when enabled."""
        os = __import__('os')
        # Backup environment and restore afterwards to avoid side effects
        old_environ = dict(os.environ)
        try:
            # Start with a clean environment to make expectations deterministic
            os.environ.clear()
            os.environ['SANDBOX_ENV_FOO'] = 'bar'
            # Create a simple sandbox config object with enable_auto_lint True
            sandbox_cfg = type("SandboxConfigStub", (), {"enable_auto_lint": True})()

            # Call function under test
            result = _default_env_vars(sandbox_cfg)

            # Assertions: custom SANDBOX_ENV_ variable included and ENABLE_AUTO_LINT set
            self.assertIn('FOO', result)
            self.assertEqual(result['FOO'], 'bar')
            self.assertIn('ENABLE_AUTO_LINT', result)
            self.assertEqual(result['ENABLE_AUTO_LINT'], 'true')
        finally:
            os.environ.clear()
            os.environ.update(old_environ)
