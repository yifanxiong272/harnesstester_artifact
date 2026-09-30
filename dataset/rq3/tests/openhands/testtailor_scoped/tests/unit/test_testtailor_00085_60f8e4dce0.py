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
        """Create a PR and verify request payload and returned URL."""
        # Create a small dummy class that uses the real mixin implementation
        class Dummy(BitBucketPRsMixin):
            def __init__(self):
                # Use a predictable base URL for assertions
                self.BASE_URL = 'https://api.bitbucket.org/2.0'

            def _extract_owner_and_repo(self, repo_name: str):
                # Simple stable splitting logic for the test
                return repo_name.split('/', 1)

            async def _make_request(self, url=None, params=None, method=None):
                # Record the inputs so we can assert them later
                self.last_request = {'url': url, 'params': params, 'method': method}
                # Return a fake response that includes the expected link structure
                data = {'links': {'html': {'href': 'https://bitbucket.org/workspace/repo/pull-requests/123'}}}
                return data, None

        inst = Dummy()

        repo_name = 'workspace/repo'
        source_branch = 'feature-branch'
        target_branch = 'main'
        title = 'Add new feature'
        body = 'This PR adds a new feature'
        draft = True

        # Import asyncio locally to avoid relying on module-level imports in the test harness
        asyncio = __import__('asyncio')

        # Run the async create_pr method
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            inst.create_pr(
                repo_name=repo_name,
                source_branch=source_branch,
                target_branch=target_branch,
                title=title,
                body=body,
                draft=draft,
            )
        )

        # Assert the returned URL is taken from the fake response
        self.assertEqual(result, 'https://bitbucket.org/workspace/repo/pull-requests/123')

        # Assert the _make_request was called with the expected URL
        expected_url = f'{inst.BASE_URL}/repositories/workspace/repo/pullrequests'
        self.assertEqual(inst.last_request['url'], expected_url)

        # Assert the payload matches what create_pr should build
        expected_payload = {
            'title': title,
            'description': body,
            'source': {'branch': {'name': source_branch}},
            'destination': {'branch': {'name': target_branch}},
            'close_source_branch': False,
            'draft': draft,
        }
        self.assertEqual(inst.last_request['params'], expected_payload)

        # Assert the correct HTTP method enum/value was passed
        self.assertEqual(inst.last_request['method'], RequestMethod.POST)
