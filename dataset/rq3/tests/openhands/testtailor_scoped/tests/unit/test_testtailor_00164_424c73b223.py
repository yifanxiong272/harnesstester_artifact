import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.resolver.interfaces.bitbucket')
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
        """Ensure Basic auth header is returned when token contains a colon (username:password)."""
        handler = BitbucketIssueHandler(
            owner='test-workspace',
            repo='test-repo',
            token='user:pass',
            username='test-user',
        )

        headers = handler.get_headers()

        # 'user:pass' base64-encoded is 'dXNlcjpwYXNz'
        expected = {
            'Authorization': 'Basic dXNlcjpwYXNz',
            'Accept': 'application/json',
        }

        self.assertEqual(headers, expected)
