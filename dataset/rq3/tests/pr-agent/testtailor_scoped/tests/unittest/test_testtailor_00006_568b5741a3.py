import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.servers.gitlab_webhook')
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
        """complete the test case here"""
        # Prepare dummy replacements for get_settings, get_logger and PRAgent used inside handle_request
        class DummySettings:
            def get(self, key, default=None):
                if key == "CONFIG.APP_NAME":
                    return "MyApp"
                return default

        class DummyLogger:
            def contextualize(self, **kwargs):
                # simple sync context manager
                class Ctx:
                    def __enter__(self_inner):
                        return self_inner
                    def __exit__(self_inner, exc_type, exc, tb):
                        return False
                return Ctx()
            def info(self, *a, **k): pass
            def warning(self, *a, **k): pass
            def error(self, *a, **k): pass
            def exception(self, *a, **k): pass

        # collect calls to the async handler to assert it was invoked properly
        called = []
        async def fake_handle_request(api_url_arg, body_arg, notify_arg=None):
            called.append((api_url_arg, body_arg, notify_arg))
            return True

        # Patch the names in the module where handle_request is defined
        target_module = handle_request.__module__
        with patch(f"{target_module}.get_settings", return_value=DummySettings()), \
             patch(f"{target_module}.get_logger", return_value=DummyLogger()), \
             patch(f"{target_module}.PRAgent") as MockAgentClass:

            # Ensure PRAgent().handle_request is our async fake
            MockAgentInstance = MockAgentClass.return_value
            MockAgentInstance.handle_request = fake_handle_request

            # ensure we have asyncio available in this test (avoid top-level imports)
            asyncio = __import__('asyncio')

            # First call: body == "/review" should set event to "pull_request"
            log_context_1 = {}
            api_url = "https://api.example/pr/1"
            body1 = "/review"
            sender_id = "user-123"
            # use a simple notify that mutates a flag
            notify_flag = {"called": False}
            def notify_fn():
                notify_flag["called"] = True

            asyncio.get_event_loop().run_until_complete(
                handle_request(api_url, body1, log_context_1, sender_id, notify=notify_fn)
            )

            self.assertEqual(log_context_1["action"], body1)
            self.assertEqual(log_context_1["event"], "pull_request")
            self.assertEqual(log_context_1["api_url"], api_url)
            self.assertEqual(log_context_1["app_name"], "MyApp")
            # ensure PRAgent.handle_request was awaited with correct arguments
            self.assertIn((api_url, body1, notify_fn), called)

            # Second call: body != "/review" should set event to "comment"
            log_context_2 = {}
            body2 = "/some-comment"
            asyncio.get_event_loop().run_until_complete(
                handle_request(api_url, body2, log_context_2, sender_id, notify=None)
            )

            self.assertEqual(log_context_2["action"], body2)
            self.assertEqual(log_context_2["event"], "comment")
            self.assertEqual(log_context_2["api_url"], api_url)
            self.assertEqual(log_context_2["app_name"], "MyApp")
            self.assertIn((api_url, body2, None), called)
