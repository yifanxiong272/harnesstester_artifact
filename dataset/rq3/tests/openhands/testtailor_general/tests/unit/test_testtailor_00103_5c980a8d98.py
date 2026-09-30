import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.github.service.prs')
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
        """Test that create_pr constructs the correct pulls URL and sends the expected payload"""
        class DummyGitHub(GitHubPRsMixin):
            BASE_URL = 'https://api.github.com'

            def __init__(self):
                self.calls = []

            # implement required abstract methods with simple stubs
            def _get_cursorrules_url(self):
                return 'https://api.github.com/unused'

            def _get_file_name_from_item(self, item):
                return 'dummy.txt'

            def _get_file_path_from_item(self, item):
                return 'path/to/dummy.txt'

            def _get_microagents_directory_params(self):
                return {}

            def _get_microagents_directory_url(self):
                return 'https://api.github.com/microagents'

            def _is_valid_microagent_file(self, item):
                return True

            async def _make_request(self, url, params=None, method=None):
                # Record call for assertions and return a fake PR response
                self.calls.append({'url': url, 'params': params, 'method': method})
                return ({'number': 123, 'html_url': 'https://github.com/owner/repo/pull/123'}, None)

        dummy = DummyGitHub()

        # Run the coroutine to create a PR using __import__ to avoid adding an import statement
        loop = __import__('asyncio').get_event_loop()
        result = loop.run_until_complete(
            dummy.create_pr(
                repo_name='owner/repo',
                source_branch='feature-branch',
                target_branch='main',
                title='Add feature',
                body=None,    # exercise default body path
                draft=True,
                labels=None
            )
        )

        # Returned URL should match the fake response
        self.assertEqual(result, 'https://github.com/owner/repo/pull/123')

        # Exactly one request should have been made (to create the PR)
        self.assertEqual(len(dummy.calls), 1)

        call = dummy.calls[0]

        # Verify the constructed URL points to the pulls endpoint for the repo
        expected_url = f'{dummy.BASE_URL}/repos/owner/repo/pulls'
        self.assertEqual(call['url'], expected_url)

        # Verify the HTTP method used is POST
        self.assertEqual(call['method'], RequestMethod.POST)

        # Verify the payload contains expected fields and default body was set correctly
        params = call['params']
        self.assertIsInstance(params, dict)
        self.assertEqual(params['title'], 'Add feature')
        self.assertEqual(params['head'], 'feature-branch')
        self.assertEqual(params['base'], 'main')
        self.assertEqual(params['body'], 'Merging changes from feature-branch into main')
        self.assertTrue(params['draft'])
