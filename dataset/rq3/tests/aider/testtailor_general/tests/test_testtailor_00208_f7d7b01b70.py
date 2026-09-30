import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.onboarding')
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
        """Simulate the temporary server raising during startup so server_error path is taken."""
        io = MagicMock()
        analytics = MagicMock()

        # Create a dummy context manager to allow find_available_port to succeed
        class DummyContextServer:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                return False

        # Side effect for socketserver.TCPServer:
        # - When handler is None (used by find_available_port), return a context manager to succeed.
        # - When handler is not None (used by run_server), raise to simulate bind/start failure.
        def fake_tcpserver(address, handler):
            if handler is None:
                return DummyContextServer()
            raise Exception("bind failed")

        # Patch the global socketserver.TCPServer so find_available_port returns a port,
        # but the server thread fails when attempting to start the real server.
        with patch("socketserver.TCPServer", side_effect=fake_tcpserver):
            # Prevent opening a browser during the test
            with patch("webbrowser.open", return_value=None):
                result = start_openrouter_oauth_flow(io, analytics)

        # The function should return None when server_error occurs
        self.assertIsNone(result)

        # Verify that io.tool_error was called with the server error message
        call_texts = [str(call.args[0]) for call in io.tool_error.call_args_list if call.args]
        self.assertTrue(
            any("Failed to start or run temporary server" in txt for txt in call_texts),
            "Expected server_error to be reported via io.tool_error",
        )
