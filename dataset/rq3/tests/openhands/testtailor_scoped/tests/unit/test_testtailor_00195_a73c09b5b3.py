import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.bitbucket_data_center.service.features')
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
        """When repository has no main branch, ResourceNotFoundError is raised."""
        async def fake_get_repository_details_from_repo_name(repository):
            class RepoDetails:
                main_branch = None
            return RepoDetails()

        # Create a simple dummy instance and bind the fake async method to it.
        dummy = type("Dummy", (), {})()
        dummy.get_repository_details_from_repo_name = fake_get_repository_details_from_repo_name

        # Use __import__ to get asyncio without adding an import statement at top-level.
        loop = __import__('asyncio').get_event_loop()

        # Call the mixin method unbound, passing our dummy as self and assert the expected error.
        with self.assertRaises(ResourceNotFoundError):
            loop.run_until_complete(
                BitbucketDCFeaturesMixin.get_microagent_content(
                    dummy, "PROJECT/repo_slug", "path/to/microagent.md"
                )
            )
