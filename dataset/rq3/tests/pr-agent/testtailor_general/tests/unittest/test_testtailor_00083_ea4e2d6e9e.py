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
        """Ensure handle_marketplace_webhooks calls get_body and logs the returned body."""
        loop = asyncio.get_event_loop()

        # Prepare a fake get_body that returns a known body
        async def fake_get_body(request):
            return {"a": 1}

        # Capture what the logger.info receives
        captured = {}
        class FakeLogger:
            def info(self, msg):
                captured['msg'] = msg

        def fake_get_logger(*args, **kwargs):
            return FakeLogger()

        # Patch the globals used by the handler to replace get_body and get_logger
        original_get_body = handle_marketplace_webhooks.__globals__.get('get_body')
        original_get_logger = handle_marketplace_webhooks.__globals__.get('get_logger')
        handle_marketplace_webhooks.__globals__['get_body'] = fake_get_body
        handle_marketplace_webhooks.__globals__['get_logger'] = fake_get_logger

        # Minimal dummy request/response objects (not used by our fake_get_body)
        class DummyRequest: pass
        class DummyResponse: pass

        try:
            # Run the async handler
            loop.run_until_complete(handle_marketplace_webhooks(DummyRequest(), DummyResponse()))

            # Verify the logger was called with the expected message format and content
            self.assertIn("Request body:\n", captured.get('msg', ''))
            self.assertIn("'a': 1", captured.get('msg', ''))
        finally:
            # Restore originals to avoid side effects on other tests
            if original_get_body is not None:
                handle_marketplace_webhooks.__globals__['get_body'] = original_get_body
            else:
                handle_marketplace_webhooks.__globals__.pop('get_body', None)
            if original_get_logger is not None:
                handle_marketplace_webhooks.__globals__['get_logger'] = original_get_logger
            else:
                handle_marketplace_webhooks.__globals__.pop('get_logger', None)
