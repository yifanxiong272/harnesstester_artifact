import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.github.service.repos')
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
        async def run_test():
            # Create a dummy subclass to provide the _make_request implementation
            # and satisfy abstract methods from the base class.
            class DummyFetcher(GitHubReposMixin):
                BASE_URL = 'https://api.github.com'

                def __init__(self):
                    self.call_count = 0

                # Minimal implementations for abstract methods on GitHubMixinBase
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

                def _is_valid_microagent_file(self, path):
                    return False

                async def _make_request(self, url, params=None):
                    # Count how many times the method was called
                    self.call_count += 1

                    # Determine the requested page (defaults to 1)
                    page = int(params.get('page', '1')) if params else 1

                    # Simulate paginated responses:
                    # page 1 -> 2 repos and a Link header indicating a next page
                    # page 2 -> 1 repo and no next link (end)
                    if page == 1:
                        response = [{'id': 1}, {'id': 2}]
                        headers = {'Link': '<https://api.github.com/?page=2>; rel="next"'}
                        return response, headers
                    elif page == 2:
                        response = [{'id': 3}]
                        headers = {}
                        return response, headers
                    else:
                        return [], {}

            fetcher = DummyFetcher()
            # Call _fetch_paginated_repos to fetch up to 3 repos
            repos = await fetcher._fetch_paginated_repos(
                'https://api.github.com/user/repos', {}, 3
            )
            return repos, fetcher.call_count

        asyncio = __import__('asyncio')
        loop = asyncio.get_event_loop()
        repos, calls = loop.run_until_complete(run_test())

        # Verify we fetched exactly 3 repositories across paginated responses
        self.assertEqual(len(repos), 3)
        self.assertEqual([r['id'] for r in repos], [1, 2, 3])
        # Ensure that _make_request was called twice (one per page)
        self.assertEqual(calls, 2)
