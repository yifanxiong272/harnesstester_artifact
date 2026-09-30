import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.servers.utils')
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
        """Valid signature should not raise and should return None."""
        # prepare inputs
        payload_body = b'{"action": "opened", "issue": 1}'
        secret_token = "supersecret_token_123"

        # compute the correct signature header as GitHub would send
        hash_object = hmac.new(secret_token.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256)
        signature_header = "sha256=" + hash_object.hexdigest()

        # should not raise an exception and should return None
        result = verify_signature(payload_body, secret_token, signature_header)
        self.assertIsNone(result)
