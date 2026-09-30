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
        """Test that handle_github_webhooks reads the body, updates context and schedules handle_request as a background task."""
        # Prepare a fake request and background tasks collector
        class DummyRequest:
            def __init__(self, headers):
                self.headers = headers

        class DummyBackgroundTasks:
            def __init__(self):
                self.called = False
                self.record = None

            def add_task(self, *args, **kwargs):
                # record the call but do not execute the task
                self.called = True
                self.record = {"args": args, "kwargs": kwargs}

        # Access the function under test from the test environment
        func = handle_github_webhooks  # assumes function is available in test globals

        # Create a sample webhook body with an installation id
        sample_body = {"installation": {"id": 12345}, "some": "payload"}

        # Replace get_body in the function globals with an async stub that returns our sample body
        async def fake_get_body(request):
            return sample_body

        # Ensure we have controllable global settings and context in the function module
        func_globals = func.__globals__
        func_globals["get_body"] = fake_get_body
        # Set a simple dict for global_settings (deepcopy will work)
        func_globals["global_settings"] = {"CONFIG": {"EXAMPLE": True}}
        # Reset context to empty dict
        func_globals["context"] = {}

        # Prepare dummy request and background tasks
        request = DummyRequest(headers={"X-GitHub-Event": "issue_comment"})
        background_tasks = DummyBackgroundTasks()
        response = object()  # not used by the handler

        # Run the async function
        asyncio = __import__("asyncio")
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(func(background_tasks, request, response))
        finally:
            try:
                loop.close()
            except Exception:
                pass

        # Assertions
        self.assertEqual(result, {}, "Handler should return an empty dict")
        self.assertTrue(background_tasks.called, "Background task should have been scheduled")
        # The first arg of add_task should be the handle_request function object from the handler's globals
        scheduled_func = background_tasks.record["args"][0]
        expected_handle_request = func_globals["handle_request"]
        self.assertIs(scheduled_func, expected_handle_request, "Scheduled function should be handle_request")
        # The scheduled positional arg after the function should be the parsed body
        scheduled_body = background_tasks.record["args"][1]
        self.assertEqual(scheduled_body, sample_body, "Scheduled task should receive the parsed body")
        # The scheduled keyword arg 'event' should match the request header
        self.assertEqual(background_tasks.record["kwargs"].get("event"), "issue_comment")
        # Context should have been updated with the installation id and settings and git_provider
        ctx = func_globals["context"]
        self.assertIn("installation_id", ctx)
        self.assertEqual(ctx["installation_id"], 12345)
        self.assertIn("settings", ctx)
        # settings should be a deepcopy of global_settings, so equal but not the same object
        self.assertEqual(ctx["settings"], func_globals["global_settings"])
        self.assertIsNot(ctx["settings"], func_globals["global_settings"])
        self.assertIn("git_provider", ctx)
        self.assertEqual(ctx["git_provider"], {})
