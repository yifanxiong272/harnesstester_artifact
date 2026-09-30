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
        """Verify set_owner updates owner, organization, project and API URLs when owner contains a slash."""
        handler = AzureDevOpsIssueHandler(
            token='test-token',
            organization='oldorg',
            project='oldproj',
            repository='test-repo',
        )

        # Sanity check initial values
        self.assertEqual(handler.owner, 'oldorg/oldproj')
        self.assertEqual(handler.organization, 'oldorg')
        self.assertEqual(handler.project, 'oldproj')
        self.assertIn('oldorg/oldproj', handler.base_api_url)

        # Call set_owner with new organization/project
        handler.set_owner('neworg/newproj')

        # Verify owner and parts were updated
        self.assertEqual(handler.owner, 'neworg/newproj')
        self.assertEqual(handler.organization, 'neworg')
        self.assertEqual(handler.project, 'newproj')

        # Verify base and derived API URLs updated accordingly and still reference the same repository
        expected_base = 'https://dev.azure.com/neworg/newproj/_apis'
        expected_repo_api = f'{expected_base}/git/repositories/test-repo'
        expected_wit = f'{expected_base}/wit'

        self.assertEqual(handler.base_api_url, expected_base)
        self.assertEqual(handler.repo_api_url, expected_repo_api)
        self.assertEqual(handler.work_items_api_url, expected_wit)
