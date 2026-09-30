import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.resolver.interfaces.azure_devops')
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
        """Verify set_owner updates owner, organization, project and related URLs."""
        # Create handler with initial values
        handler = AzureDevOpsIssueHandler(
            token='token-x',
            organization='orig-org',
            project='orig-proj',
            repository='test-repo',
        )

        # Set owner with "org/project" form -> should update organization and project
        handler.set_owner('new-org/new-proj')

        self.assertEqual(handler.owner, 'new-org/new-proj')
        self.assertEqual(handler.organization, 'new-org')
        self.assertEqual(handler.project, 'new-proj')

        expected_base = 'https://dev.azure.com/new-org/new-proj/_apis'
        self.assertEqual(handler.base_api_url, expected_base)

        expected_repo_api = f'{expected_base}/git/repositories/{handler.repository}'
        self.assertEqual(handler.repo_api_url, expected_repo_api)

        expected_wit = f'{expected_base}/wit'
        self.assertEqual(handler.work_items_api_url, expected_wit)

        # Now set owner to a single-part string -> should only set owner, not change org/project
        handler.set_owner('just-an-owner')
        self.assertEqual(handler.owner, 'just-an-owner')
        # organization and project should remain as previously set
        self.assertEqual(handler.organization, 'new-org')
        self.assertEqual(handler.project, 'new-proj')
