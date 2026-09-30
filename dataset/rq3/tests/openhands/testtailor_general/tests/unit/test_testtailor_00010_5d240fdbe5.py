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
        """Ensure environment variables prefixed with SANDBOX_ENV_ are included without the prefix,
        and that enable_auto_lint in the config sets/overrides ENABLE_AUTO_LINT to 'true'."""
        # Scenario 1: multiple SANDBOX_ENV_ keys are picked up and non-prefixed keys are ignored
        env = {
            'SANDBOX_ENV_FOO': 'bar',
            'SANDBOX_ENV_BAZ': 'qux',
            'OTHER_VAR': 'ignored',
        }
        with patch.dict('os.environ', env, clear=True):
            cfg = SandboxConfig()
            cfg.enable_auto_lint = False
            result = _default_env_vars(cfg)

            self.assertIn('FOO', result)
            self.assertEqual(result['FOO'], 'bar')
            self.assertIn('BAZ', result)
            self.assertEqual(result['BAZ'], 'qux')
            self.assertNotIn('OTHER_VAR', result)
            self.assertNotIn('ENABLE_AUTO_LINT', result)

        # Scenario 2: when config.enable_auto_lint is True, ENABLE_AUTO_LINT is set to 'true'
        # even if an environment variable SANDBOX_ENV_ENABLE_AUTO_LINT exists (it should be overwritten)
        env2 = {'SANDBOX_ENV_ENABLE_AUTO_LINT': 'override_value'}
        with patch.dict('os.environ', env2, clear=True):
            cfg2 = SandboxConfig()
            cfg2.enable_auto_lint = True
            result2 = _default_env_vars(cfg2)

            # The environment-provided value should be overwritten by the config flag
            self.assertIn('ENABLE_AUTO_LINT', result2)
            self.assertEqual(result2['ENABLE_AUTO_LINT'], 'true')
