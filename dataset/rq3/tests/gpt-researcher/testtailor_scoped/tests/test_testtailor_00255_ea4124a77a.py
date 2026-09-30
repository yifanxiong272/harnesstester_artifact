import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.serper.serper')
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
        # Ensure missing SERPER_API_KEY raises the expected Exception
        expected_msg = ("Serper API key not found. Please set the SERPER_API_KEY environment variable. "
                        "You can get a key at https://serper.dev/")
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(Exception) as cm:
                # Instantiation triggers get_api_key in __init__
                SerperSearch(query="test query")
            self.assertEqual(str(cm.exception), expected_msg)

        # Ensure when SERPER_API_KEY is present it is returned and stored on the instance
        with patch.dict(os.environ, {"SERPER_API_KEY": "fake-serper-key"}, clear=False):
            s = SerperSearch(query="test query")
            self.assertEqual(s.api_key, "fake-serper-key")
            # Also verify calling get_api_key directly returns the same value
            self.assertEqual(s.get_api_key(), "fake-serper-key")
