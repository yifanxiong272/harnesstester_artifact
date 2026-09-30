import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.resolver.interfaces.bitbucket_data_center')
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
        """Token contains no ':' and username is not provided -> token should be used as-is for Basic auth."""
        handler = BitbucketDCIssueHandler(
            owner='PROJ',
            repo='my-repo',
            token='baretoken',
            base_domain='dc.example.com',
        )
        expected = base64.b64encode(b'baretoken').decode()
        self.assertIn('Authorization', handler.headers)
        self.assertEqual(handler.headers['Authorization'], f'Basic {expected}')
        self.assertEqual(handler.headers.get('Accept'), 'application/json')
