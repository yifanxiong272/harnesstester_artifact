import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.forgejo.service.prs')
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
        """Ensure string 'repository' value is split and response keys are normalized."""
        asyncio = __import__('asyncio')

        class DummyForgejo(ForgejoPRsMixin):
            def __init__(self):
                # capture calls for assertions
                self.captured = {}
                self.user_id = None

            # Implement required abstract methods with simple stubs
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

            def _is_valid_microagent_file(self, filename):
                return False

            def _split_repo(self, repository):
                # record input and return fixed owner/repo
                self.captured['split_input'] = repository
                return ('ownerX', 'repoY')

            def _build_repo_api_url(self, owner, repo_name, *parts):
                # record how this is called and return a predictable URL
                self.captured['build_args'] = (owner, repo_name, parts)
                return f"https://api.example.com/repos/{owner}/{repo_name}/" + "/".join(parts)

            async def _make_request(self, url, payload=None, method=None):
                # record call and return a response missing 'number' and 'html_url'
                self.captured['make_request_args'] = (url, payload, method)
                return ({'index': 123, 'url': 'http://example.com/pr/123'}, None)

        dummy = DummyForgejo()
        # prepare input with repository as a string so _split_repo is used
        input_data = {'repository': 'ignored/by_split', 'title': 'Test PR'}

        # run the async method using a fresh event loop
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(dummy.create_pull_request(input_data))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        # Assertions: _split_repo was called with the original repository string
        self.assertEqual(dummy.captured['split_input'], 'ignored/by_split')

        # _build_repo_api_url should have been called with values returned from _split_repo
        build_owner, build_repo, build_parts = dummy.captured['build_args']
        self.assertEqual(build_owner, 'ownerX')
        self.assertEqual(build_repo, 'repoY')
        self.assertIn('pulls', build_parts)

        # _make_request should receive the payload without the 'repository' key
        req_url, req_payload, req_method = dummy.captured['make_request_args']
        self.assertEqual(req_payload, {'title': 'Test PR'})
        self.assertEqual(req_url, "https://api.example.com/repos/ownerX/repoY/pulls")
        self.assertEqual(req_method, RequestMethod.POST)

        # The returned result should have 'number' copied from 'index' and 'html_url' from 'url'
        self.assertEqual(result['number'], 123)
        self.assertEqual(result['html_url'], 'http://example.com/pr/123')
