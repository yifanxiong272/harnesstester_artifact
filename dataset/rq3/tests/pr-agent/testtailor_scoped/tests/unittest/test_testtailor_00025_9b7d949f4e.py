import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.servers.azuredevops_server_webhook')
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
        """Test that handle_request_comment sets log_context entries and interacts with provider when the agent handles the request."""
        mod = handle_request_comment.__module__

        url = "http://example.com/pr/1"
        body = "/ask please do something"
        thread_id = 123
        comment_id = 456
        log_context = {}

        # Create a fake provider with the methods used by handle_request_comment
        class FakeProvider:
            def __init__(self):
                self.replied = None
                self.status_set = None
                self.removed = False

            def reply_to_thread(self, t_id, b, is_temp):
                self.replied = (t_id, b, is_temp)
                return None

            def set_thread_status(self, t_id, status):
                self.status_set = (t_id, status)

            def remove_initial_comment(self):
                self.removed = True

        provider = FakeProvider()

        # Dummy logger that supports .contextualize(...) as a context manager
        class DummyLogger:
            def contextualize(self, **kwargs):
                class Ctx:
                    def __enter__(self_inner):
                        return self_inner
                    def __exit__(self_inner, exc_type, exc, tb):
                        return False
                return Ctx()
            def exception(self, *a, **k):
                pass
            def info(self, *a, **k):
                pass

        # Dummy PRAgent whose handle_request calls notify() and returns True to simulate handling
        class DummyPRAgent:
            async def handle_request(self, pr_url_arg, body_arg, notify=None):
                if notify:
                    notify()
                return True

        # Patch dependencies in the module where handle_request_comment is defined
        with patch(f"{mod}.PRAgent", new=DummyPRAgent), \
             patch(f"{mod}.get_git_provider_with_context", return_value=provider), \
             patch(f"{mod}.handle_line_comment", side_effect=lambda b, tid, p: b), \
             patch(f"{mod}.get_logger", new=lambda *a, **k: DummyLogger()):

            # Run the async function using import to avoid top-level import statements
            asyncio = __import__("asyncio")
            asyncio.run(handle_request_comment(url, body, thread_id, comment_id, log_context))

        # Assertions: log_context should have been updated before entering try block
        self.assertIn("action", log_context)
        self.assertEqual(log_context["action"], body)
        self.assertIn("api_url", log_context)
        self.assertEqual(log_context["api_url"], url)

        # Provider should have been replied to (via notify), thread status set and initial comment removed
        self.assertIsNotNone(provider.replied)
        self.assertEqual(provider.replied[0], thread_id)
        self.assertEqual(provider.status_set, (thread_id, "closed"))
        self.assertTrue(provider.removed)
