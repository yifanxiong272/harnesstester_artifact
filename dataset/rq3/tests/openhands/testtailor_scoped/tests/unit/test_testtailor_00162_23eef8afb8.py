import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.bitbucket.service.repos')
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
        """When query contains a workspace prefix (contains '/'), search_repositories
        should split the query and call get_paginated_repos with the workspace and repo parts."""
        # Arrange
        called = {}

        class DummyService(BitBucketReposMixin):
            BASE_URL = "https://api.bitbucket.org/2.0"

            async def get_paginated_repos(self, page, per_page, sort, installation_id, query=None):
                # record what was called and return a fake repository list
                called['args'] = (page, per_page, sort, installation_id, query)
                return [{"full_name": f"{installation_id}/{query}", "id": "1"}]

            async def get_installations(self):
                # Should not be called for this test; if it is, fail the test
                raise AssertionError("get_installations should not be called when query contains '/'")

        service = DummyService()

        # Act
        asyncio = __import__('asyncio')
        result = asyncio.run(
            service.search_repositories(
                query="my-workspace/some-repo-query",
                per_page=7,
                sort="full_name",
                order="asc",
                public=False,
                app_mode=AppMode.OPENHANDS,
            )
        )

        # Assert
        self.assertEqual(result, [{"full_name": "my-workspace/some-repo-query", "id": "1"}])
        self.assertIn('args', called)
        self.assertEqual(called['args'][0], 1)  # page
        self.assertEqual(called['args'][1], 7)  # per_page
        self.assertEqual(called['args'][2], "full_name")  # sort passed through
        self.assertEqual(called['args'][3], "my-workspace")  # workspace slug
        self.assertEqual(called['args'][4], "some-repo-query")  # repo_query
