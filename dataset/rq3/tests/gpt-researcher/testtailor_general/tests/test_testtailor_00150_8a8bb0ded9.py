import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.xquik.xquik')
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
        """When XQUIK_API_KEY is missing, initializing XquikSearch raises the expected Exception."""
        # Ensure environment has no XQUIK_API_KEY to trigger the KeyError path.
        with patch.dict(os.environ, {}, clear=True):
            expected_msg = (
                "Xquik API key not found. Please set the XQUIK_API_KEY "
                "environment variable. Get a key at https://xquik.com"
            )
            with self.assertRaises(Exception) as cm:
                # Creating the instance calls get_api_key() in __init__, which should raise.
                XquikSearch("some query")
            self.assertEqual(str(cm.exception), expected_msg)
