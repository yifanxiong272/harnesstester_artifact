import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.servers.github_polling')
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
        """Ensure that when the PATCH response status is not 205, an error is logged and the correct URL is used."""
        errors = []

        class DummyLogger:
            def error(self, msg):
                errors.append(msg)

        # Patch the get_logger used by the function under test by injecting into its globals
        original_get_logger = mark_notification_as_read.__globals__.get('get_logger')
        mark_notification_as_read.__globals__['get_logger'] = lambda *a, **k: DummyLogger()

        notification = {'id': 'abc123'}
        headers = {'Authorization': 'token'}

        class DummyResponse:
            def __init__(self, status):
                self.status = status

        class DummyCM:
            def __init__(self, resp):
                self._resp = resp

            async def __aenter__(self):
                return self._resp

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class DummySession:
            def __init__(self):
                self.last_url = None
                self.last_headers = None

            def patch(self, url, headers):
                # record arguments for assertion and return an async context manager
                self.last_url = url
                self.last_headers = headers
                # return a response with a non-205 status to trigger the error branch
                return DummyCM(DummyResponse(500))

        sess = DummySession()

        try:
            # run the async function
            asyncio.get_event_loop().run_until_complete(
                mark_notification_as_read(headers, notification, sess)
            )

            # assertions: error was logged and URL was formed correctly
            self.assertEqual(len(errors), 1)
            self.assertIn("Failed to mark notification as read. Status code: 500", errors[0])
            expected_url = f"https://api.github.com/notifications/threads/{notification['id']}"
            self.assertEqual(sess.last_url, expected_url)
            self.assertIs(sess.last_headers, headers)
        finally:
            # restore original get_logger to avoid side effects on other tests
            if original_get_logger is None:
                mark_notification_as_read.__globals__.pop('get_logger', None)
            else:
                mark_notification_as_read.__globals__['get_logger'] = original_get_logger
