import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.bitbucket_data_center.service.base')
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
        """Ensure _extract_owner_and_repo raises ValueError for invalid repository format."""
        # Dynamically import the service class and SecretStr to avoid top-level import statements
        svc_module = __import__(
            'openhands.integrations.bitbucket_data_center.bitbucket_dc_service',
            fromlist=['BitbucketDCService'],
        )
        svc_cls = getattr(svc_module, 'BitbucketDCService')
        pyd = __import__('pydantic', fromlist=['SecretStr'])
        SecretStr = getattr(pyd, 'SecretStr')

        svc = svc_cls(token=SecretStr('tok'), base_domain='host.example.com')
        invalid_repo = 'invalidrepo'  # no '/' present -> should be considered invalid

        with self.assertRaises(ValueError) as cm:
            svc._extract_owner_and_repo(invalid_repo)

        self.assertIn(f'Invalid repository name: {invalid_repo}', str(cm.exception))
