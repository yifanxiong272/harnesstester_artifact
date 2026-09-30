import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.identity_providers.__init__')
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
        """Trigger ValueError when configured identity provider is unknown."""
        # Save originals
        orig_get_settings = get_identity_provider.__globals__['get_settings']
        orig_providers = get_identity_provider.__globals__['_IDENTITY_PROVIDERS']

        try:
            # Create a fake settings object that returns a provider id that does not exist
            missing_provider_id = "this_provider_does_not_exist_12345"

            class FakeSettings:
                def get(self, key, default=None):
                    return missing_provider_id

            # Patch the get_settings used by get_identity_provider
            get_identity_provider.__globals__['get_settings'] = lambda: FakeSettings()

            # Ensure the missing id is not present in the providers mapping for the test
            providers_copy = dict(orig_providers)
            providers_copy.pop(missing_provider_id, None)
            get_identity_provider.__globals__['_IDENTITY_PROVIDERS'] = providers_copy

            # Expect ValueError with the correct message
            with self.assertRaisesRegex(ValueError, rf"Unknown identity provider: {missing_provider_id}"):
                get_identity_provider()
        finally:
            # Restore originals
            get_identity_provider.__globals__['get_settings'] = orig_get_settings
            get_identity_provider.__globals__['_IDENTITY_PROVIDERS'] = orig_providers
