import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.azure_devops.service.repos')
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
        """Verify search_repositories filters by query, limits by per_page, and builds full_name."""
        # Create a minimal client that uses the mixin and provides required attributes/methods
        class DummyClient(AzureDevOpsReposMixin):
            def __init__(self):
                self._base_url = 'https://dev.azure.com/myorg'
                self.organization = 'myorg'
                self.last_url = None

            # Provide base_url property expected by the mixin
            @property
            def base_url(self):
                return self._base_url

            # Stubs for abstract methods not used by the test but required to instantiate
            def _get_cursorrules_url(self):
                return ""

            def _get_file_name_from_item(self, item):
                return ""

            def _get_file_path_from_item(self, item):
                return ""

            def _get_microagents_directory_params(self):
                return {}

            def _get_microagents_directory_url(self):
                return ""

            def _is_valid_microagent_file(self, name):
                return False

            async def _make_request(self, url):
                # record the URL called and return a simulated Azure DevOps response
                self.last_url = url
                response = {
                    'value': [
                        {
                            'id': '1',
                            'name': 'Alpha',
                            'project': {'name': 'ProjectA'},
                        },
                        {
                            'id': '2',
                            'name': 'Beta',
                            'project': {'name': 'ProjectBeta'},
                        },
                        {
                            'id': '3',
                            'name': 'Gamma',
                            'project': {'name': 'ProjectG'},
                        },
                    ]
                }
                return response, None

        client = DummyClient()

        # Run the async method using a local event loop to avoid relying on outer imports
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(
                client.search_repositories(query='be', per_page=1)
            )
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        # Verify the correct API URL was called
        expected_url = f'{client.base_url}/_apis/git/repositories?api-version=7.1'
        self.assertEqual(client.last_url, expected_url)

        # Should filter to only 'Beta' (case-insensitive) and then limit to per_page=1
        self.assertEqual(len(results), 1)
        repo = results[0]
        self.assertEqual(repo.full_name, 'myorg/ProjectBeta/Beta')
        self.assertEqual(repo.git_provider, ProviderType.AZURE_DEVOPS)
        self.assertFalse(repo.is_public)
