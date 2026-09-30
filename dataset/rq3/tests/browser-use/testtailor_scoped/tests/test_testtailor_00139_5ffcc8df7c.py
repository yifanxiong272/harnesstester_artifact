import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.mistral.chat')
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
        """Test that _get_api_key prefers instance api_key, falls back to MISTRAL_API_KEY, and raises when missing."""
        env_key = 'MISTRAL_API_KEY'
        prev = os.environ.get(env_key)
        try:
            # Ensure env var present
            os.environ[env_key] = 'env-value-123'

            # Instance-level api_key should take precedence over env var
            inst = ChatMistral(api_key='instance-value-abc')
            self.assertEqual(inst._get_api_key(), 'instance-value-abc')

            # If instance api_key is None, fallback to env var
            inst2 = ChatMistral(api_key=None)
            self.assertEqual(inst2._get_api_key(), 'env-value-123')

            # Remove both and ensure ModelProviderError is raised with 401
            os.environ.pop(env_key, None)
            inst3 = ChatMistral(api_key=None)
            with self.assertRaises(ModelProviderError) as cm:
                inst3._get_api_key()
            exc = cm.exception
            self.assertEqual(exc.status_code, 401)
            self.assertEqual(exc.message, 'Missing Mistral API key')
            # model name should match default model
            self.assertEqual(exc.model, inst3.name)
        finally:
            # restore environment
            if prev is not None:
                os.environ[env_key] = prev
            else:
                os.environ.pop(env_key, None)
