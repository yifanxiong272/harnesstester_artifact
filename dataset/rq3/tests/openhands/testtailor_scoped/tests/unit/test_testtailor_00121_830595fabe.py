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
        """Ensure search_events returns immediately on 404 from the remote API."""
        # Create a NestedEventStore with a session API key so headers are set
        store = NestedEventStore(
            base_url='http://test-api.example.com',
            sid='test-session',
            user_id='test-user',
            session_api_key='test-api-key',
        )

        mock_response = MagicMock()
        # Simulate a 404 from the remote endpoint
        mock_response.status_code = 404

        with patch('httpx.get') as mock_get:
            mock_get.return_value = mock_response

            # Calling search_events should return an empty iterable (no events yielded)
            events = list(store.search_events())

            self.assertEqual(events, [])
            mock_get.assert_called_once_with(
                'http://test-api.example.com/events?start_id=0&reverse=False',
                headers={'X-Session-API-Key': 'test-api-key'},
            )
