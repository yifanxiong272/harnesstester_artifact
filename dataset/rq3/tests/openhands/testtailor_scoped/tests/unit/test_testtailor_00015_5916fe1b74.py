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
        """Verify RemoteRuntimeBuilder __init__ sets attributes and updates session headers."""
        api_url = 'https://example.test/api'
        api_key = 'super-secret-key'

        # Case A: session not provided -> new HttpSession is created and header set
        builder = RemoteRuntimeBuilder(api_url, api_key)
        self.assertEqual(builder.api_url, api_url)
        self.assertEqual(builder.api_key, api_key)
        self.assertIsInstance(builder.session, HttpSession)
        self.assertIn('X-API-Key', builder.session.headers)
        self.assertEqual(builder.session.headers['X-API-Key'], api_key)

        # Case B: session provided -> same session object is used and header is updated
        custom_session = HttpSession()
        # pre-populate a header to ensure it is preserved
        custom_session.headers.update({'Existing-Header': 'keep-me'})
        builder_with_custom = RemoteRuntimeBuilder(api_url, api_key, session=custom_session)
        self.assertIs(builder_with_custom.session, custom_session)
        self.assertIn('Existing-Header', custom_session.headers)
        self.assertEqual(custom_session.headers['Existing-Header'], 'keep-me')
        self.assertIn('X-API-Key', custom_session.headers)
        self.assertEqual(custom_session.headers['X-API-Key'], api_key)
