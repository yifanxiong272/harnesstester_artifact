import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.storage.data_models.secrets')
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
        """Ensure provider_tokens_serializer skips entries where provider_token.token is falsy."""
        # Create a MappingProxyType with a ProviderToken whose token is an empty string
        # (empty string is falsy and should be skipped by the serializer)
        mp = MappingProxyType({ProviderType.GITHUB: ProviderToken(token='')})
        secrets = Secrets(provider_tokens=mp)

        # model_dump triggers the field serializer
        dumped = secrets.model_dump()

        # provider_tokens serializer should skip the entry with empty token and return an empty mapping
        self.assertIn('provider_tokens', dumped)
        self.assertEqual(dumped['provider_tokens'], {})
