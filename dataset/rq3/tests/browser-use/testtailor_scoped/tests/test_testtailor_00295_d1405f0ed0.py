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
        """Verify that MISTRAL_BASE_URL env var overrides base_url and trailing slashes are stripped."""
        # Preserve original environment value
        original = os.environ.get('MISTRAL_BASE_URL', None)
        try:
            # Case 1: env var present with trailing slash -> should override and strip trailing slash
            os.environ['MISTRAL_BASE_URL'] = 'https://custom.example.com/api/'
            model = ChatMistral()
            result = model._get_base_url()
            self.assertEqual(result, 'https://custom.example.com/api')

            # Case 2: env var unset -> fallback to instance base_url and strip trailing slash
            os.environ.pop('MISTRAL_BASE_URL', None)
            model2 = ChatMistral()
            model2.base_url = 'https://api.mistral.ai/v1/'
            result2 = model2._get_base_url()
            self.assertEqual(result2, 'https://api.mistral.ai/v1')
        finally:
            # Restore original environment value
            if original is None:
                os.environ.pop('MISTRAL_BASE_URL', None)
            else:
                os.environ['MISTRAL_BASE_URL'] = original
