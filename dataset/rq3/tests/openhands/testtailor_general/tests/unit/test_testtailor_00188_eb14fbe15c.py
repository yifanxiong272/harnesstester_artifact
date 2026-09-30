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
        """Verify that when 'repository' is a string the mixin uses _split_repo
        and that response 'index' -> 'number' and 'url' -> 'html_url' are set.
        """
        called = {}

        class Dummy(ForgejoPRsMixin):
            def __init__(self):
                # user_id should not be used because repository is provided
                self.user_id = 'should-not-be-used'

            # Implement abstract methods from base to avoid instantiation error
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

            def _split_repo(self, repository):
                called['split_repo_arg'] = repository
                return ('alice', 'example')

            def _build_repo_api_url(self, owner, repo, *parts):
                called['build_url_args'] = (owner, repo, parts)
                return 'http://api/forges/repos/alice/example/pulls'

            async def _make_request(self, url, payload=None, method=None):
                called['make_request_args'] = (url, payload, method)
                # simulate Forgejo response that uses 'index' and 'url' keys
                return ({'index': 123, 'url': 'http://forgejo/pr/123', 'some': 'value'}, None)

        dummy = Dummy()
        asyncio = __import__('asyncio')
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                dummy.create_pull_request({'repository': 'alice/example', 'title': 'Test PR'})
            )
        finally:
            try:
                loop.close()
            except Exception:
                pass

        # Ensure _split_repo was used with the provided repository string
        self.assertEqual(called.get('split_repo_arg'), 'alice/example')
        # Ensure _build_repo_api_url received the owner/repo returned by _split_repo
        self.assertEqual(called.get('build_url_args')[0], 'alice')
        self.assertEqual(called.get('build_url_args')[1], 'example')
        # Ensure _make_request was called and returned response was normalized
        self.assertEqual(result.get('number'), 123)
        self.assertEqual(result.get('html_url'), 'http://forgejo/pr/123')
        # Preserve other keys from the original response
        self.assertEqual(result.get('some'), 'value')
