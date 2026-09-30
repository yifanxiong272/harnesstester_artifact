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
        """Trigger an exception inside handle_request_comment and assert logger.exception is called with expected args."""
        url = "http://example.com/pr/1"
        body = "do it"  # not starting with '/ask ' to avoid provider usage in handle_line_comment
        thread_id = 1
        comment_id = 2
        log_context = {}

        # Prepare a mock logger that provides a contextualize context manager and records exception calls
        mock_logger = MagicMock()

        class _Ctx:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        mock_logger.contextualize = lambda **k: _Ctx(**k)
        mock_logger.exception = MagicMock()

        # Create a fake PRAgent whose handle_request raises an exception to force the except branch
        class FakePRAgent:
            def __init__(self, *args, **kwargs):
                pass

            async def handle_request(self, pr_url, request, notify=None):
                raise Exception("boom")

        # Prepare a dummy git provider to be returned by get_git_provider_with_context (not actually used here)
        dummy_provider = MagicMock()

        # Patch the names used inside handle_request_comment by modifying its globals
        func_globals = handle_request_comment.__globals__
        originals = {
            "get_logger": func_globals.get("get_logger"),
            "PRAgent": func_globals.get("PRAgent"),
            "get_git_provider_with_context": func_globals.get("get_git_provider_with_context"),
        }
        func_globals["get_logger"] = lambda *a, **k: mock_logger
        func_globals["PRAgent"] = FakePRAgent
        func_globals["get_git_provider_with_context"] = lambda pr_url: dummy_provider

        try:
            # Run the async function using __import__ to avoid relying on a top-level asyncio import
            __import__("asyncio").run(handle_request_comment(url, body, thread_id, comment_id, log_context))

            # Assertions: logger.exception should have been called once with expected parameters
            mock_logger.exception.assert_called_once()
            called_args, called_kwargs = mock_logger.exception.call_args
            # first positional arg is the message
            self.assertTrue(len(called_args) >= 1)
            self.assertIn("Failed to handle webhook", called_args[0])
            # check artifact and error kwargs
            self.assertIn("artifact", called_kwargs)
            self.assertEqual(called_kwargs["artifact"], {"url": url, "body": body})
            self.assertIn("error", called_kwargs)
            self.assertEqual(called_kwargs["error"], "boom")
        finally:
            # Restore originals
            for name, val in originals.items():
                if val is None:
                    if name in func_globals:
                        del func_globals[name]
                else:
                    func_globals[name] = val
