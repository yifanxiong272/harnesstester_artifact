import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.google.chat')
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
        """Ensure that when importlib.metadata.version raises PackageNotFoundError,
        the x-goog-api-client header uses 'browser-use/unknown'."""
        import importlib
        from browser_use.llm.google.chat import ChatGoogle

        # Patch importlib.metadata.version to raise PackageNotFoundError to hit the except branch
        original_version = importlib.metadata.version

        def _raise_not_found(name):
            raise importlib.metadata.PackageNotFoundError

        importlib.metadata.version = _raise_not_found
        try:
            chat = ChatGoogle(model='gemini-flash-latest', api_key='fake')
            params = chat._get_client_params()
            http_opts = params.get('http_options', {})
            headers = http_opts.get('headers', {})

            self.assertIn('x-goog-api-client', headers, 'x-goog-api-client header missing')
            # Should specifically use 'unknown' when package not found
            self.assertEqual(headers['x-goog-api-client'], 'browser-use/unknown')
        finally:
            # Restore original function to avoid side effects on other tests
            importlib.metadata.version = original_version
