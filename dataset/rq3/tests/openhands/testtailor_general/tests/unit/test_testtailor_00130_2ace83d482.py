import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.bitbucket_data_center.service.branches')
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
        """Calling get_paginated_branches with an invalid repository string
        (no slash) should raise a ValueError."""
        class Dummy(BitbucketDCBranchesMixin):
            # Provide minimal stubs so the method can be invoked
            def _extract_owner_and_repo(self, repository: str):
                # Return something valid so the function continues to the split check
                return ("owner", "repo")

            def _repo_api_base(self, owner: str, repo: str) -> str:
                return "http://example.local"

            async def _make_request(self, url, params):
                # Should not be reached in this test because ValueError is raised first
                return {}, None

        dummy = Dummy()

        # Import asyncio at runtime to avoid adding top-level imports in this snippet
        asyncio = __import__('asyncio')
        loop = asyncio.new_event_loop()
        try:
            with self.assertRaisesRegex(ValueError, r'Invalid repository name: invalidrepo'):
                loop.run_until_complete(dummy.get_paginated_branches("invalidrepo"))
        finally:
            loop.close()
