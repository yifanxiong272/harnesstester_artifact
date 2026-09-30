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
        # Import asyncio dynamically to avoid requiring top-level import in this snippet
        asyncio = __import__('asyncio')

        # Ensure we have a fresh loop for running async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Prepare placeholders to observe calls
            called = []

            # Fake settings object with .get(...) used by the target code
            class FakeSettings:
                def __init__(self, app_name):
                    self._app_name = app_name

                def get(self, key, default=None):
                    if key == "CONFIG.APP_NAME":
                        return self._app_name
                    return default

            # Fake logger context manager returned by contextualize(...)
            class FakeLoggerCtx:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

            # Fake logger exposing contextualize method
            class FakeLogger:
                def contextualize(self, **kwargs):
                    # Accept any contextualization keys and return a context manager
                    return FakeLoggerCtx()

            # Fake PRAgent whose handle_request is async and records calls
            class FakePRAgent:
                def __init__(self, *args, **kwargs):
                    pass

                async def handle_request(self, api_url, body, notify=None):
                    called.append((api_url, body, notify))
                    return True

            # Patch the function globals used by handle_request to inject fakes
            g = handle_request.__globals__
            original_get_settings = g.get("get_settings")
            original_get_logger = g.get("get_logger")
            original_PRAgent = g.get("PRAgent")

            try:
                g["get_settings"] = lambda: FakeSettings("MyTestApp")
                g["get_logger"] = lambda: FakeLogger()
                g["PRAgent"] = FakePRAgent

                # First invocation: body equals "/review" -> event should be "pull_request"
                log_context = {}
                loop.run_until_complete(
                    handle_request("https://api.example.com", "/review", log_context, "sender-id-1")
                )

                self.assertEqual(log_context["action"], "/review")
                self.assertEqual(log_context["event"], "pull_request")
                self.assertEqual(log_context["api_url"], "https://api.example.com")
                self.assertEqual(log_context["app_name"], "MyTestApp")

                # Second invocation: other body -> event should be "comment"
                log_context2 = {}
                loop.run_until_complete(
                    handle_request("https://other.api", "some comment", log_context2, "sender-id-2")
                )

                self.assertEqual(log_context2["action"], "some comment")
                self.assertEqual(log_context2["event"], "comment")
                self.assertEqual(log_context2["api_url"], "https://other.api")
                self.assertEqual(log_context2["app_name"], "MyTestApp")

                # Ensure PRAgent.handle_request was called for both invocations
                self.assertEqual(len(called), 2)
                self.assertEqual(called[0][0], "https://api.example.com")
                self.assertEqual(called[0][1], "/review")
                self.assertEqual(called[1][0], "https://other.api")
                self.assertEqual(called[1][1], "some comment")
            finally:
                # Restore originals
                if original_get_settings is not None:
                    g["get_settings"] = original_get_settings
                else:
                    g.pop("get_settings", None)
                if original_get_logger is not None:
                    g["get_logger"] = original_get_logger
                else:
                    g.pop("get_logger", None)
                if original_PRAgent is not None:
                    g["PRAgent"] = original_PRAgent
                else:
                    g.pop("PRAgent", None)
        finally:
            loop.close()
