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
    @patch("threading.Thread")
    def test_case_XX(self, mock_thread_class):
        """Simulate the server thread never starting so server_started.wait times out."""
        io = MagicMock()
        analytics = MagicMock()

        # Ensure the function finds a port quickly by overriding its find_available_port
        orig_find = start_openrouter_oauth_flow.__globals__.get("find_available_port")
        start_openrouter_oauth_flow.__globals__["find_available_port"] = lambda: 8542

        # Dummy Thread that never runs the target (so server_started is never set)
        class DummyThread:
            def __init__(self, target=None, daemon=None):
                self._target = target
                self.daemon = daemon

            def start(self):
                # Do not invoke the target; simulate thread never starting
                return None

            def join(self, timeout=None):
                return None

        mock_thread_class.side_effect = lambda *args, **kwargs: DummyThread(*args, **kwargs)

        try:
            result = start_openrouter_oauth_flow(io, analytics)
        finally:
            # Restore original find_available_port to avoid side effects on other tests
            if orig_find is None:
                del start_openrouter_oauth_flow.__globals__["find_available_port"]
            else:
                start_openrouter_oauth_flow.__globals__["find_available_port"] = orig_find

        # The call should time out waiting for the server to start and return None
        self.assertIsNone(result)
        io.tool_error.assert_any_call("Temporary authentication server failed to start in time.")
        mock_thread_class.assert_called()
