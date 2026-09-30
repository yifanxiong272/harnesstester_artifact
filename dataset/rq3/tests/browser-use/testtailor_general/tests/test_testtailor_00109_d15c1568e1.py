import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.browser_use.chat')
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
        """ChatBrowserUse constructor raises when BROWSER_USE_API_KEY is not set."""
        import os

        # Import here so test file-level fixtures that set env vars can be overridden.
        from browser_use import ChatBrowserUse

        # Preserve and remove any existing env var, ensuring the constructor sees it as missing.
        previous = os.environ.pop('BROWSER_USE_API_KEY', None)
        try:
            with self.assertRaises(ValueError) as cm:
                # No api_key passed and env var removed -> should raise the expected ValueError
                ChatBrowserUse()
            msg = str(cm.exception)
            self.assertIn('BROWSER_USE_API_KEY is not set', msg)
            self.assertIn('https://cloud.browser-use.com/new-api-key', msg)
        finally:
            # Restore environment to avoid affecting other tests
            if previous is not None:
                os.environ['BROWSER_USE_API_KEY'] = previous
