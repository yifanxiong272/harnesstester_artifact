import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.bitbucket_data_center.service.repos')
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
        """When public is True and the URL contains '/projects/<key>/<repo>',
        search_repositories should call get_repository_details_from_repo_name
        and return the repository result.
        """
        async def runner():
            # Minimal subclass implementing the required async helper
            class Dummy(BitbucketDCReposMixin):
                async def get_repository_details_from_repo_name(self, full_name):
                    # Return a simple dict to verify it is propagated
                    return {'full_name': full_name}

            client = Dummy()
            query = 'http://example.com/projects/PROJ/my-repo'
            result = await client.search_repositories(
                query=query,
                per_page=10,
                sort='',
                order='',
                public=True,
                app_mode=AppMode.OPENHANDS,
            )
            return result

        asyncio_mod = __import__('asyncio')
        try:
            loop = asyncio_mod.get_event_loop()
        except RuntimeError:
            loop = asyncio_mod.new_event_loop()
            asyncio_mod.set_event_loop(loop)
        result = loop.run_until_complete(runner())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['full_name'], 'PROJ/my-repo')
