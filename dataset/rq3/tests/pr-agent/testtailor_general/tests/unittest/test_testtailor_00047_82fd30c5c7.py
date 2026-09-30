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
    def test_case_01(self):
        """Raise 403 when x-hub-signature-256 header is missing."""
        payload_body = b'{"action": "opened"}'
        secret_token = "supersecret"
        signature_header = None  # triggers the not signature_header condition

        with self.assertRaises(HTTPException) as ctx:
            verify_signature(payload_body, secret_token, signature_header)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail, "x-hub-signature-256 header is missing!")
