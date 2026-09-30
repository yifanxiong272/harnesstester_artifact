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
        """Test get_installations returns list of string IDs from the installations response."""
        class DummyRepoClient(GitHubReposMixin):
            BASE_URL = 'https://api.github.com'

            # Implement required abstract methods as simple stubs
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
                return False

            async def _make_request(self, url, params=None):
                # Simulate GitHub API response with mixed int and str ids
                response = {'installations': [{'id': 123}, {'id': '456'}]}
                headers = {}
                return response, headers

        client = DummyRepoClient()

        # Use __import__ to avoid requiring a top-level import in this snippet
        asyncio = __import__('asyncio')
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(client.get_installations())
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        self.assertEqual(result, ['123', '456'])
