import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.server.routes.secrets')
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
        """complete the test case here"""
        # Create a Secrets object with one provider token entry using plain dict format
        provider_tokens = {
            'github': {
                'token': 'dummy-token',
                'host': 'example.com',
                'user_id': 'user-123',
            }
        }
        original_secrets = Secrets(provider_tokens=provider_tokens)

        # Create Settings containing the secrets_store with that provider token
        settings = Settings(secrets_store=original_secrets)

        # Create simple async stub stores for secrets_store and settings_store
        class DummySecretsStore:
            def __init__(self):
                self.stored = None

            async def store(self, secrets: Secrets) -> None:
                self.stored = secrets

        class DummySettingsStore:
            def __init__(self):
                self.stored = None

            async def store(self, settings_obj: Settings) -> None:
                self.stored = settings_obj

        secrets_store_mock = DummySecretsStore()
        settings_store_mock = DummySettingsStore()

        # Run the migration function in a fresh event loop
        asyncio = __import__('asyncio')
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                invalidate_legacy_secrets_store(settings, settings_store_mock, secrets_store_mock)
            )
        finally:
            loop.close()

        # Verify the migration returned the expected Secrets object
        self.assertIsInstance(result, Secrets)
        self.assertEqual(dict(result.provider_tokens), dict(original_secrets.provider_tokens))

        # Verify secrets_store.store was called once with the migrated secrets
        self.assertIsNotNone(secrets_store_mock.stored)
        self.assertIsInstance(secrets_store_mock.stored, Secrets)
        self.assertEqual(dict(secrets_store_mock.stored.provider_tokens), dict(original_secrets.provider_tokens))

        # Verify settings_store.store was called once with settings that have an empty secrets_store
        self.assertIsNotNone(settings_store_mock.stored)
        self.assertIsInstance(settings_store_mock.stored, Settings)
        self.assertEqual(len(dict(settings_store_mock.stored.secrets_store.provider_tokens)), 0)
