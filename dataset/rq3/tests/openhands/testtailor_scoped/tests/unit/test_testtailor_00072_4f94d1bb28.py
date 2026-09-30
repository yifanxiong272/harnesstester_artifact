import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.gitlab.service.prs')
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
        called = {}

        class Dummy(GitLabPRsMixin):
            BASE_URL = 'https://gitlab.example.com/api/v4'

            # Implement abstract methods from GitLabMixinBase so the class can be instantiated
            def _get_cursorrules_url(self):
                return ''

            def _get_file_name_from_item(self, item):
                return ''

            def _get_file_path_from_item(self, item):
                return ''

            def _get_microagents_directory_params(self):
                return {}

            def _get_microagents_directory_url(self):
                return ''

            def _is_valid_microagent_file(self, filename):
                return True

            async def _make_request(self, url, params=None, method=None):
                called['url'] = url
                called['params'] = params
                called['method'] = method
                # Simulate GitLab response shape expected by create_mr
                return {'web_url': 'https://gitlab.example.com/mr/1'}, None

        inst = Dummy()

        # import asyncio at runtime to avoid top-level import requirement in this snippet
        asyncio = __import__('asyncio')

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                inst.create_mr(
                    id='owner/repo',
                    source_branch='feature-branch',
                    target_branch='main',
                    title='Add feature',
                    description=None,
                    labels=['bug', 'urgent'],
                )
            )
        finally:
            loop.close()

        # The method should return the web_url from the fake response
        self.assertEqual(result, 'https://gitlab.example.com/mr/1')

        # Verify that the project id in the URL was URL-encoded (slash -> %2F)
        expected_url = 'https://gitlab.example.com/api/v4/projects/owner%2Frepo/merge_requests'
        self.assertEqual(called.get('url'), expected_url)

        # Verify that labels were joined into a comma-separated string in params
        self.assertIn('labels', called.get('params', {}))
        self.assertEqual(called['params']['labels'], 'bug,urgent')

        # Verify default description was set when None was provided
        self.assertEqual(
            called['params']['description'],
            'Merging changes from feature-branch into main'
        )

        # Verify the request method was POST
        self.assertEqual(called['method'], RequestMethod.POST)
