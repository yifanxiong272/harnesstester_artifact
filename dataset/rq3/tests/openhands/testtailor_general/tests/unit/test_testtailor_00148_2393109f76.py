import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.azure_devops.azure_devops_service')
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
        """Ensure base_domain with protocol is parsed and organization is extracted."""
        # Provide a base_domain that includes a protocol and domain portion so that
        # the code path with domain_path.split('://', 1)[1] is executed, and the
        # subsequent split('/', 1)[1] removes the domain, leaving the org/path.
        service = AzureDevOpsService(
            user_id='test_user',
            token=None,
            base_domain='https://dev.azure.com/myorg/project',
        )

        # organization should be the first path segment after the domain
        self.assertEqual(service.organization, 'myorg')

        # base_url property should reflect the parsed organization
        self.assertEqual(service.base_url, 'https://dev.azure.com/myorg')
