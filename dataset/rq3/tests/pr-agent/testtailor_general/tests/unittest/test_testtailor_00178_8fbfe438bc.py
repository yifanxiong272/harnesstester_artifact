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
        """Trigger the mismatch branch to raise the 'Request signatures didn't match!' HTTPException."""
        # prepare inputs
        payload_body = b'{"action":"opened","issue":{"number":1}}'
        secret_token = "supersecret"
        # provide a header that is present but does not match the expected signature
        signature_header = "sha256=invalidsignature"

        with self.assertRaises(HTTPException) as cm:
            verify_signature(payload_body, secret_token, signature_header)

        exc = cm.exception
        # Verify it's the expected 403 and the correct detail message
        self.assertEqual(exc.status_code, 403)
        self.assertEqual(exc.detail, "Request signatures didn't match!")
