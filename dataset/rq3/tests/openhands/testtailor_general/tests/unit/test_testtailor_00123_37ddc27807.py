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
        """Search repositories should call the correct Azure DevOps URL, filter by query, and respect per_page."""
        # Create a dummy instance that will be passed as 'self' to the mixin method
        class Dummy:
            def __init__(self):
                # set attributes expected by the mixin
                self.base_url = 'https://dev.azure.com/myorg'
                self.organization = 'myorg'
                self._last_url = None

            async def _make_request(self, url):
                # record the requested URL so we can assert it was called correctly
                self._last_url = url
                # return a fake response containing multiple repositories
                return (
                    {
                        'value': [
                            {
                                'id': '123',
                                'name': 'foo-repo',
                                'project': {'name': 'ProjectA'},
                            },
                            {
                                'id': '456',
                                'name': 'bar-repo',
                                'project': {'name': 'ProjectA'},
                            },
                        ]
                    },
                    None,
                )

        dummy = Dummy()

        # Manually drive the coroutine without importing asyncio.
        coro = AzureDevOpsReposMixin.search_repositories(
            dummy, query='foo', per_page=1
        )
        # Step the coroutine to the first await; it should yield the inner coroutine from _make_request
        try:
            awaited = coro.send(None)
        except StopIteration as stop:
            # coroutine finished immediately (unlikely here)
            results = stop.value
        else:
            # Run the awaited inner coroutine to completion (our Dummy._make_request doesn't await anything)
            try:
                awaited.send(None)
            except StopIteration as inner_stop:
                inner_result = inner_stop.value
            else:
                # If inner coroutine required further driving (not expected), try to get its return via attribute
                inner_result = None

            # Resume outer coroutine with the result of the awaited call
            try:
                coro.send(inner_result)
            except StopIteration as stop:
                results = stop.value

        # Assert the mixin called the expected Azure DevOps repositories endpoint
        expected_url = f'{dummy.base_url}/_apis/git/repositories?api-version=7.1'
        self.assertEqual(dummy._last_url, expected_url)

        # Assert filtering by query worked and per_page limited results to 1
        self.assertEqual(len(results), 1)
        repo = results[0]
        self.assertEqual(repo.id, '123')
        self.assertEqual(repo.full_name, 'myorg/ProjectA/foo-repo')
        self.assertEqual(repo.git_provider, ProviderType.AZURE_DEVOPS)
        self.assertFalse(repo.is_public)
