import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.utils.http_session')
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
        """When HttpSession.request is called after close, logger.error is invoked and _is_closed is reset."""
        # Create an HttpSession instance and set it as closed
        session = HttpSession()
        # Ensure headers exist and set a default header to verify merging behavior
        session.headers = {'X-Default': '1'}
        session._is_closed = True

        # Prepare a mock client whose request method we can inspect/return a value from
        mock_client = MagicMock()
        mock_client.request.return_value = "mock-response"

        module_path = HttpSession.__module__

        # Patch the module-level _get_client to return our mock client and patch logger.error
        with patch(f"{module_path}._get_client", return_value=mock_client) as mock_get_client, patch(
            f"{module_path}.logger.error"
        ) as mock_logger_error:
            # Call request with additional headers to ensure merge and to trigger the closed-path
            result = session.request('GET', 'https://example.test/', headers={'X-Test': '2'})

            # Verify the logger.error was called once due to using session after close
            mock_logger_error.assert_called_once()

            # After logging the error, _is_closed should have been reset to False
            assert session._is_closed is False

            # Verify _get_client was used and client.request was invoked with merged headers
            mock_get_client.assert_called_once()
            mock_client.request.assert_called_once()

            # Inspect the actual call arguments to client.request
            called_args, called_kwargs = mock_client.request.call_args
            # First two positional args should be method and URL
            assert called_args[0] == 'GET'
            assert called_args[1] == 'https://example.test/'

            # Headers should be merged: session.headers overridden/extended by provided headers
            expected_headers = {'X-Default': '1', 'X-Test': '2'}
            assert called_kwargs.get('headers') == expected_headers

            # The result from session.request should be the mock client's return value
            assert result == "mock-response"
