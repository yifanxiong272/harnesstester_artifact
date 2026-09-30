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
        """Ensure handle_marketplace_webhooks logs the body returned by get_body."""
        # Prepare a fake async get_body that returns a predictable dict
        async def fake_get_body(request):
            return {"ok": "yes"}

        # Prepare a fake logger that captures info messages
        class FakeLogger:
            def __init__(self):
                self.messages = []

            def info(self, msg):
                self.messages.append(msg)

        fake_logger = FakeLogger()

        # Patch the globals used by the function under test to inject our fakes
        original_get_body = handle_marketplace_webhooks.__globals__.get("get_body")
        original_get_logger = handle_marketplace_webhooks.__globals__.get("get_logger")
        try:
            handle_marketplace_webhooks.__globals__["get_body"] = fake_get_body
            handle_marketplace_webhooks.__globals__["get_logger"] = lambda: fake_logger

            # Call the async function
            import asyncio
            loop = asyncio.get_event_loop()
            loop.run_until_complete(handle_marketplace_webhooks(request=object(), response=object()))

            # Verify the logger was called with the expected message including the body
            self.assertEqual(len(fake_logger.messages), 1)
            logged = fake_logger.messages[0]
            self.assertIn("Request body:", logged)
            self.assertIn(str({"ok": "yes"}), logged)
        finally:
            # Restore originals to avoid side effects on other tests
            if original_get_body is not None:
                handle_marketplace_webhooks.__globals__["get_body"] = original_get_body
            else:
                handle_marketplace_webhooks.__globals__.pop("get_body", None)
            if original_get_logger is not None:
                handle_marketplace_webhooks.__globals__["get_logger"] = original_get_logger
            else:
                handle_marketplace_webhooks.__globals__.pop("get_logger", None)
