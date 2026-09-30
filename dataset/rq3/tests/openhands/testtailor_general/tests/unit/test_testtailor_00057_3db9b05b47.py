import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.builder.remote')
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
        """Ensure RemoteRuntimeBuilder stores api_url/api_key and updates session.headers."""
        # Prepare inputs
        api_url = 'https://example.test/api'
        api_key = 'my-secret-key'

        # Create a dummy session to ensure the provided session is used and updated
        class DummySession:
            def __init__(self):
                self.headers = {'Existing-Header': 'keep-me'}

        dummy_session = DummySession()

        # Instantiate with a provided session
        builder = RemoteRuntimeBuilder(api_url, api_key, session=dummy_session)

        # Verify attributes are set
        self.assertEqual(builder.api_url, api_url)
        self.assertEqual(builder.api_key, api_key)

        # The provided session object should be used (same identity)
        self.assertIs(builder.session, dummy_session)

        # The X-API-Key header should have been added and existing headers preserved
        self.assertIn('X-API-Key', dummy_session.headers)
        self.assertEqual(dummy_session.headers['X-API-Key'], api_key)
        self.assertEqual(dummy_session.headers['Existing-Header'], 'keep-me')

        # Instantiate with session=None to exercise the default HttpSession creation
        api_url2 = 'https://another.example'
        api_key2 = 'another-key'
        builder2 = RemoteRuntimeBuilder(api_url2, api_key2, session=None)

        # Verify attributes for the second builder
        self.assertEqual(builder2.api_url, api_url2)
        self.assertEqual(builder2.api_key, api_key2)

        # The default session should be an HttpSession and have the header set
        self.assertIsInstance(builder2.session, HttpSession)
        self.assertIn('X-API-Key', builder2.session.headers)
        self.assertEqual(builder2.session.headers['X-API-Key'], api_key2)
