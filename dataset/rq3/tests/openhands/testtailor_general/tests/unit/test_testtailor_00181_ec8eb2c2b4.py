import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.events.nested_event_store')
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
        """Ensure search_events returns immediately when the remote endpoint is 404."""
        with patch('httpx.get') as mock_get:
            # Create a NestedEventStore with a session_api_key so headers are set
            event_store = NestedEventStore(
                base_url='http://test-api.example.com',
                sid='test-session',
                user_id='test-user',
                session_api_key='test-api-key',
            )

            # Mock the HTTP response to simulate a 404 from the server
            mock_response = MagicMock()
            mock_response.status_code = 404  # matches status.HTTP_404_NOT_FOUND
            mock_get.return_value = mock_response

            # Calling search_events should immediately return (no events)
            events = list(event_store.search_events())
            self.assertEqual(events, [])

            # Verify the HTTP call was made with expected parameters and headers
            mock_get.assert_called_once_with(
                'http://test-api.example.com/events?start_id=0&reverse=False',
                headers={'X-Session-API-Key': 'test-api-key'},
            )
