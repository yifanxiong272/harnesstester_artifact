import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.google.google')
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
        """When GOOGLE_API_KEY is missing, GoogleSearch.__init__ raises an informative Exception and does not call get_cx_key."""
        # Ensure environment has no GOOGLE_API_KEY (and nothing else) and that get_cx_key is not invoked
        with patch.dict('os.environ', {}, clear=True):
            with patch.object(GoogleSearch, 'get_cx_key', autospec=True) as mock_cx:
                with self.assertRaises(Exception) as cm:
                    GoogleSearch(query="some query")
                # Verify the raised exception message is the expected informative one
                self.assertIn("Google API key not found. Please set the GOOGLE_API_KEY environment variable", str(cm.exception))
                # Because get_api_key raised, get_cx_key should not have been called during initialization
                mock_cx.assert_not_called()
