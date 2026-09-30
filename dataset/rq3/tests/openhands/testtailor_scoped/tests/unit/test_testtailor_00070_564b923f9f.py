import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.bitbucket_data_center.service.prs')
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
        """Ensure create_pr returns the first html link when 'html' is a non-empty list."""
        asyncio = __import__('asyncio')

        class Dummy(BitbucketDCPRsMixin):
            def _extract_owner_and_repo(self, repo_name):
                # Return owner and repo as expected by the method
                return ('PROJ', 'repo')

            def _repo_api_base(self, owner, repo):
                return f'https://bitbucket.local/projects/{owner}/repos/{repo}/rest/api/1.0'

            async def _make_request(self, url, params=None, method=None):
                # Validate we are being called to create a pull request
                assert url.endswith('/pull-requests')
                # Return data where 'links' is a dict and 'html' is a non-empty list
                data = {
                    'links': {
                        'html': [
                            {'href': 'https://bitbucket.local/projects/PROJ/repos/repo/pull-requests/42'}
                        ]
                    }
                }
                return data, None

        inst = Dummy()
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                inst.create_pr('PROJ/repo', 'feature-branch', 'main', 'My PR', 'Description')
            )
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        self.assertEqual(
            result,
            'https://bitbucket.local/projects/PROJ/repos/repo/pull-requests/42'
        )
