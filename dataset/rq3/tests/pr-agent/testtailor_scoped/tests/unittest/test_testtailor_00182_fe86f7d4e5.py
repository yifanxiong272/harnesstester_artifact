import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.servers.github_app')
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
        """When a webhook_secret is set, the body bytes are read and the signature is verified."""
        # prepare body and bytes (avoid using external modules)
        body = {"action": "opened", "number": 1}
        body_bytes = b'{"action":"opened","number":1}'

        # secret and signature header (value itself is arbitrary because we'll patch verification)
        secret = "supersecret"
        signature_header_value = "sha256=dummy"

        # dummy request with async json() and body()
        class DummyRequest:
            def __init__(self):
                self.headers = {"x-hub-signature-256": signature_header_value}

            async def json(self):
                return body

            async def body(self):
                return body_bytes

        req = DummyRequest()

        # prepare settings object with github.webhook_secret without using types.SimpleNamespace
        class DummyGithub:
            def __init__(self, webhook_secret):
                self.webhook_secret = webhook_secret

        class DummySettings:
            def __init__(self, github):
                self.github = github

        settings = DummySettings(DummyGithub(secret))

        # patch the get_settings and verify_signature used by get_body by updating its globals entry, restore after
        gl = get_body.__globals__
        original_get_settings = gl.get("get_settings")
        original_verify = gl.get("verify_signature")

        called = []

        def fake_verify(payload_body, secret_token, signature_header):
            # assert that get_body passes the expected values to verify_signature
            assert payload_body == body_bytes
            assert secret_token == secret
            assert signature_header == signature_header_value
            called.append(True)

        try:
            gl["get_settings"] = lambda: settings
            gl["verify_signature"] = fake_verify
            result = asyncio.get_event_loop().run_until_complete(get_body(req))
        finally:
            # restore originals
            gl["get_settings"] = original_get_settings
            gl["verify_signature"] = original_verify

        self.assertEqual(result, body)
        # ensure our fake verification was invoked
        self.assertTrue(called)
