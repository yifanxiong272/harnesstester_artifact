import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.api.server')
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
        """Ensure that when a live thread exists for the session, its stop() is invoked."""
        # Create a fake thread that reports alive and records stop() calls
        class FakeThread:
            def __init__(self):
                self.stop_called = False

            def is_alive(self):
                return True

            def stop(self):
                self.stop_called = True

            def __repr__(self):
                return "<FakeThread>"

        fake_thread = FakeThread()

        # Use the test client to set a known session id so we can register the thread
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["session_id"] = "test-session-123"

            # Insert our fake thread into the server THREADS mapping for that session
            THREADS["test-session-123"] = fake_thread

            # Call the /stop endpoint
            response = client.get("/stop")

        # Assert the endpoint returned the expected status and the thread stop was called
        self.assertEqual(response.status_code, 202)
        self.assertTrue(fake_thread.stop_called)

        # Cleanup
        THREADS.pop("test-session-123", None)
