import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.bitbucket.service.prs')
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
        """Test that create_pr constructs the correct payload, calls _make_request with POST,
        and returns the html link from the response."""
        import asyncio

        async def run_test():
            # Minimal dummy class that provides the bits the mixin expects
            class Dummy(BitBucketPRsMixin):
                BASE_URL = 'https://api.bitbucket.org/2.0'

                def __init__(self):
                    self._seen_repo_name = None

                def _extract_owner_and_repo(self, repo_name: str):
                    # record that this was called with the expected repo_name
                    self._seen_repo_name = repo_name
                    return ('workspace', 'repo-slug')

                async def _make_request(self, url, params=None, method=None):
                    # Validate that the URL was constructed as expected
                    expected_url = f'{self.BASE_URL}/repositories/workspace/repo-slug/pullrequests'
                    assert url == expected_url, f'Unexpected url: {url}'
                    # Validate payload contents
                    assert params['title'] == 'Test Title'
                    assert params['description'] == 'Test body'
                    assert params['source']['branch']['name'] == 'feature-branch'
                    assert params['destination']['branch']['name'] == 'main'
                    assert params['close_source_branch'] is False
                    assert params['draft'] is True
                    # Ensure correct HTTP method enum is used
                    assert method == RequestMethod.POST
                    # Return a payload containing the expected link structure
                    return ({'links': {'html': {'href': 'https://bitbucket.org/workspace/repo-slug/pull-requests/1'}}}, None)

            client = Dummy()

            # Call the async method under test
            result = await client.create_pr(
                repo_name='workspace/repo-slug',
                source_branch='feature-branch',
                target_branch='main',
                title='Test Title',
                body='Test body',
                draft=True,
            )

            # Verify returned URL and that _extract_owner_and_repo was used
            self.assertEqual(result, 'https://bitbucket.org/workspace/repo-slug/pull-requests/1')
            self.assertEqual(client._seen_repo_name, 'workspace/repo-slug')

        # Run the coroutine
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(run_test())
