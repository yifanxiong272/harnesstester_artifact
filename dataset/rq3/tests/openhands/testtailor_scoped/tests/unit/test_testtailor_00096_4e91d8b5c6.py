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
        """HttpSession.request logs an error and resets _is_closed when used after close."""
        # Create an HttpSession instance
        session = HttpSession()
        # Ensure some default headers to exercise header merging
        session.headers = {'Existing': 'value'}
        # Mark the session as closed to take the branch
        session._is_closed = True

        # Prepare a mock client to be returned by the module-level _get_client
        mock_client = MagicMock()
        mock_client.request.return_value = 'mock-response'

        # Obtain the module where HttpSession is defined so we can patch its globals
        module = __import__(HttpSession.__module__, fromlist=['*'])

        # Patch _get_client and the module logger to observe their usage
        with patch.object(module, '_get_client', return_value=mock_client) as mock_get_client, patch.object(
            module, 'logger'
        ) as mock_logger:
            # Call request with explicit headers to ensure merging happens
            result = session.request('GET', 'https://example.com', headers={'Extra': 'hdr'})

            # Verify we got the mocked response back
            assert result == 'mock-response'

            # The session._is_closed should have been reset to False by the method
            assert session._is_closed is False

            # _get_client should have been called to obtain the client
            mock_get_client.assert_called_once()

            # The client's request should have been invoked with our args
            mock_client.request.assert_called_once()
            called_args, called_kwargs = mock_client.request.call_args

            # First two positional args should be method and URL
            assert called_args[0] == 'GET'
            assert called_args[1] == 'https://example.com'

            # Headers should be merged: session.headers take precedence only where keys don't collide
            assert 'headers' in called_kwargs
            assert called_kwargs['headers']['Existing'] == 'value'
            assert called_kwargs['headers']['Extra'] == 'hdr'

            # Ensure logger.error was called to report usage after close, with expected kwargs
            mock_logger.error.assert_called_once()
            _, error_kwargs = mock_logger.error.call_args
            # The message should be the expected string
            # (positional first arg of the error call)
            assert mock_logger.error.call_args[0][0] == 'Session is being used after close!'
            assert error_kwargs.get('stack_info') is True
            assert error_kwargs.get('exc_info') is True
