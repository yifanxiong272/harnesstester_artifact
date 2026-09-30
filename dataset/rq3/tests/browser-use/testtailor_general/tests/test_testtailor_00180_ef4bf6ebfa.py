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
    def test_bu_version_missing_sets_unknown(self):
        """When importlib.metadata.version raises PackageNotFoundError, header uses 'unknown'."""
        # Patch importlib.metadata.version to raise PackageNotFoundError to exercise the except branch
        with unittest.mock.patch('importlib.metadata.version', side_effect=importlib.metadata.PackageNotFoundError):
            chat = ChatGoogle(model='gemini-flash-latest', api_key='fake')
            params = chat._get_client_params()
            http_opts = params.get('http_options', {})
            header = http_opts.get('headers', {}).get('x-goog-api-client')

            self.assertIsNotNone(header, 'x-goog-api-client header should be present')
            self.assertEqual(header, 'browser-use/unknown', 'Header should use "unknown" when package not found')
