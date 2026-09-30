import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.core.setup')
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
        """Test that FORGEJO_TOKEN is picked up and FORGEJO_BASE_URL is normalized to host."""
        from unittest.mock import patch
        from openhands.integrations.provider import ProviderType
        from openhands.core.setup import get_provider_tokens

        # Case 1: Base URL includes protocol and an API path -> should extract netloc
        with patch.dict(
            os.environ,
            {'FORGEJO_TOKEN': 'secret123', 'FORGEJO_BASE_URL': 'https://codeberg.org/api/v1'},
            clear=False,
        ):
            provider_tokens = get_provider_tokens()
            self.assertIsNotNone(provider_tokens)
            self.assertIn(ProviderType.FORGEJO, provider_tokens)
            forgejo_token = provider_tokens[ProviderType.FORGEJO]
            self.assertEqual(forgejo_token.token.get_secret_value(), 'secret123')
            self.assertEqual(forgejo_token.host, 'codeberg.org')

        # Case 2: Base URL without protocol but with path -> should strip path and use host
        with patch.dict(
            os.environ,
            {'FORGEJO_TOKEN': 'another-secret', 'FORGEJO_BASE_URL': 'forgejo.example.com/some/path'},
            clear=False,
        ):
            provider_tokens = get_provider_tokens()
            self.assertIsNotNone(provider_tokens)
            self.assertIn(ProviderType.FORGEJO, provider_tokens)
            forgejo_token = provider_tokens[ProviderType.FORGEJO]
            self.assertEqual(forgejo_token.token.get_secret_value(), 'another-secret')
            self.assertEqual(forgejo_token.host, 'forgejo.example.com')
