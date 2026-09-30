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
        """Ensure handle_request_comment sets log_context keys 'action' and 'api_url'."""
        url = "https://dev.azure.com/org/project/_git/repo/pullrequest/42"
        body = "run-some-command"
        thread_id = 1001
        comment_id = 2002
        log_context = {}

        # module where the function is defined
        module_name = handle_request_comment.__module__

        # Prepare a fake logger with a contextualize context manager
        mock_logger = MagicMock()

        class DummyCtx:
            def __init__(self, *args, **kwargs):
                # accept arbitrary contextualize kwargs
                pass

            def __enter__(self):
                return mock_logger

            def __exit__(self, exc_type, exc, tb):
                return False

        mock_logger.contextualize = lambda **kwargs: DummyCtx()
        mock_logger.exception = MagicMock()
        mock_logger.info = MagicMock()

        # Dummy PRAgent that simply returns True from handle_request
        class DummyPRAgent:
            def __init__(self):
                pass

            async def handle_request(self, pr_url, request, notify=None):
                return True

        # Dummy provider with required methods used in handle_request_comment
        provider = MagicMock()
        provider.reply_to_thread = MagicMock()
        provider.set_thread_status = MagicMock()
        provider.remove_initial_comment = MagicMock()
        # Ensure get_thread_context returns None so handle_line_comment leaves body unchanged
        provider.get_thread_context.return_value = None

        # Patch get_logger, PRAgent and get_git_provider_with_context in the function's module
        with patch(f"{module_name}.get_logger", return_value=mock_logger):
            with patch(f"{module_name}.PRAgent", DummyPRAgent):
                with patch(f"{module_name}.get_git_provider_with_context", return_value=provider):
                    # Run the async function using __import__ to avoid needing an import statement
                    __import__("asyncio").run(handle_request_comment(url, body, thread_id, comment_id, log_context))

        # Verify that the log_context was updated as expected
        self.assertIn("action", log_context)
        self.assertIn("api_url", log_context)
        self.assertEqual(log_context["action"], body)
        self.assertEqual(log_context["api_url"], url)
