import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.azure_devops.service.features')
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
        """Test AzureDevOpsFeaturesMixin.get_user returns a User built from the authenticatedUser payload."""
        # Obtain asyncio without using an import statement (allowed in test body)
        asyncio = __import__('asyncio')

        class DummyAzureDevOps(AzureDevOpsFeaturesMixin):
            # Provide base_url as a class attribute to satisfy any abstract requirement
            base_url = 'https://dev.azure.com/exampleorg'

            async def _make_request(self, url, *args, **kwargs):
                # Return a response that includes an authenticatedUser dict
                return (
                    {
                        'authenticatedUser': {
                            'id': 987,
                            'providerDisplayName': 'Jane Developer',
                            'descriptor': 'descriptor-value',
                        }
                    },
                    None,
                )

        dummy = DummyAzureDevOps()

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            user = loop.run_until_complete(dummy.get_user())
        finally:
            try:
                loop.close()
            finally:
                try:
                    asyncio.set_event_loop(None)
                except Exception:
                    pass

        # Validate the returned User model fields
        self.assertIsInstance(user, User)
        self.assertEqual(user.id, '987')  # should be converted to string
        self.assertEqual(user.login, 'Jane Developer')
        self.assertEqual(user.name, 'Jane Developer')
        self.assertEqual(user.avatar_url, '')
        self.assertEqual(user.email, '')
        self.assertIsNone(user.company)
