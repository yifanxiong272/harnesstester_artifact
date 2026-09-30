import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.models')
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
        """Ensure top-level Mistral alias resolves to ChatMistral with env vars."""
        prev_key = os.environ.get('MISTRAL_API_KEY')
        prev_base = os.environ.get('MISTRAL_BASE_URL')

        os.environ['MISTRAL_API_KEY'] = 'mistral-test-key'
        os.environ['MISTRAL_BASE_URL'] = 'https://custom.mistral'

        try:
            llm = get_llm_by_name('mistral_large')

            self.assertIsInstance(llm, ChatMistral)
            self.assertEqual(llm.model, 'mistral-large-latest')
            self.assertEqual(llm.api_key, 'mistral-test-key')
            # base_url may be a httpx.URL or str; normalize to str for comparison
            self.assertEqual(str(llm.base_url).rstrip('/'), 'https://custom.mistral')
        finally:
            if prev_key is None:
                os.environ.pop('MISTRAL_API_KEY', None)
            else:
                os.environ['MISTRAL_API_KEY'] = prev_key

            if prev_base is None:
                os.environ.pop('MISTRAL_BASE_URL', None)
            else:
                os.environ['MISTRAL_BASE_URL'] = prev_base
