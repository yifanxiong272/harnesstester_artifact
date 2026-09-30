import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.gitlab.service.resolver')
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
        """Test fetching a single discussion returns processed notes inline."""
        class DummyResolver(GitLabResolverMixin):
            BASE_URL = 'https://gitlab.example/api/v4'

            # Implement abstract methods from base so the class can be instantiated.
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

            def _is_valid_microagent_file(self, name):
                return False

            async def _make_request(self, url, params=None):
                # Basic sanity checks that the URL was constructed as expected.
                assert url.startswith(self.BASE_URL)
                assert '/merge_requests/' in url
                assert '/discussions/' in url

                notes = [
                    {
                        'id': 1,
                        'body': 'First comment',
                        'author': {'username': 'alice'},
                        'created_at': '2021-01-01T00:00:00Z',
                        'updated_at': '2021-01-01T01:00:00Z',
                        'system': False,
                    },
                    {
                        'id': 2,
                        'body': 'Second comment',
                        'author': {'username': 'bob'},
                        'created_at': '2021-01-02T00:00:00Z',
                        'updated_at': '2021-01-02T01:00:00Z',
                        'system': False,
                    },
                ]
                return {'notes': notes}, {}

        resolver = DummyResolver()
        # Run the async method from the synchronous test using __import__ to avoid top-level imports
        aio = __import__('asyncio')
        try:
            loop = aio.get_event_loop()
            result = loop.run_until_complete(
                resolver.get_review_thread_comments('my/project', 42, 'discussion-123')
            )
        except RuntimeError:
            # If no event loop or already running, fall back to asyncio.run
            result = aio.run(
                resolver.get_review_thread_comments('my/project', 42, 'discussion-123')
            )

        # Validate results were processed into Comment objects with expected data
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].id, '1')
        self.assertEqual(result[0].body, 'First comment')
        self.assertEqual(result[0].author, 'alice')
        self.assertEqual(result[1].id, '2')
        self.assertEqual(result[1].body, 'Second comment')
        self.assertEqual(result[1].author, 'bob')
        # Ensure ordering by created_at
        self.assertTrue(result[0].created_at < result[1].created_at)
