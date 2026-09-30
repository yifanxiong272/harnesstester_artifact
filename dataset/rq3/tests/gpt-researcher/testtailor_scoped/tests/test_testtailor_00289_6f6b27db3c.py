import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('multi_agents.agents.utils.llms')
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
        """Trigger an exception in the LLM call and assert the error handling path is executed."""
        # Save originals
        orig_create = call_model.__globals__.get("create_chat_completion")
        orig_logger = call_model.__globals__.get("logger")

        # Create an async stub that raises
        async def _raise_exc(*args, **kwargs):
            raise RuntimeError("boom")

        # Bring in needed stdlib modules without top-level imports
        io = __import__("io")
        sys = __import__("sys")
        asyncio = __import__("asyncio")

        try:
            # Replace create_chat_completion and logger in the function globals
            call_model.__globals__["create_chat_completion"] = _raise_exc
            mock_logger = unittest.mock.MagicMock()
            call_model.__globals__["logger"] = mock_logger

            # Capture stdout by swapping sys.stdout
            saved_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(
                        call_model(prompt=[{"role": "user", "content": "hello"}], model="any-model")
                    )
                finally:
                    loop.close()
            finally:
                output = sys.stdout.getvalue()
                sys.stdout = saved_stdout

            # The function prints a warning; ensure it was printed
            self.assertIn("⚠️ Error in calling model", output)

            # The logger.error should have been called with the exception message
            mock_logger.error.assert_called()
            logged_arg = mock_logger.error.call_args[0][0]
            self.assertIn("Error in calling model", logged_arg)
            self.assertIn("boom", logged_arg)

            # When an exception occurs the function returns None
            self.assertIsNone(result)
        finally:
            # Restore originals to avoid side effects on other tests
            if orig_create is not None:
                call_model.__globals__["create_chat_completion"] = orig_create
            else:
                call_model.__globals__.pop("create_chat_completion", None)
            if orig_logger is not None:
                call_model.__globals__["logger"] = orig_logger
            else:
                call_model.__globals__.pop("logger", None)
