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
        """Ensure constructing ChatBrowserUse without an API key raises the expected ValueError."""
        import os
        from browser_use import ChatBrowserUse

        # Ensure the environment variable is not set for this test, restoring it afterwards.
        prev_key = os.environ.pop('BROWSER_USE_API_KEY', None)
        try:
            with self.assertRaises(ValueError) as cm:
                ChatBrowserUse()  # no api_key provided and env var removed -> should raise

            message = str(cm.exception)
            self.assertIn('BROWSER_USE_API_KEY is not set', message)
            self.assertIn('https://cloud.browser-use.com/new-api-key', message)
        finally:
            if prev_key is not None:
                os.environ['BROWSER_USE_API_KEY'] = prev_key
