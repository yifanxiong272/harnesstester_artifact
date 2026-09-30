import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.skills.service')
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
        """Verify api_key resolution and ValueError behavior in SkillService.__init__"""
        # Preserve any existing environment variable and ensure a clean starting state
        original_env_value = os.environ.get('BROWSER_USE_API_KEY')
        if 'BROWSER_USE_API_KEY' in os.environ:
            del os.environ['BROWSER_USE_API_KEY']

        try:
            # 1) Explicit api_key parameter should be used as-is
            svc_explicit = SkillService(skill_ids=['skill-1', 'skill-2'], api_key='explicit-key')
            self.assertEqual(svc_explicit.skill_ids, ['skill-1', 'skill-2'])
            self.assertEqual(svc_explicit.api_key, 'explicit-key')
            self.assertFalse(svc_explicit._initialized)

            # 2) If api_key is None, environment variable should be used
            os.environ['BROWSER_USE_API_KEY'] = 'env-key'
            svc_from_env = SkillService(skill_ids=['skill-x'], api_key=None)
            self.assertEqual(svc_from_env.skill_ids, ['skill-x'])
            self.assertEqual(svc_from_env.api_key, 'env-key')
            self.assertFalse(svc_from_env._initialized)

            # 3) If neither api_key nor env var is set, initialization should raise ValueError
            del os.environ['BROWSER_USE_API_KEY']
            with self.assertRaises(ValueError):
                SkillService(skill_ids=['missing-key'], api_key=None)

        finally:
            # Restore original environment
            if original_env_value is not None:
                os.environ['BROWSER_USE_API_KEY'] = original_env_value
            else:
                os.environ.pop('BROWSER_USE_API_KEY', None)
