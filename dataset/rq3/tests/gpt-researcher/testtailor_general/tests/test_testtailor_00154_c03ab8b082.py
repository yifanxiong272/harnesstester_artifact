import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.bing.bing')
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
        """When BING_API_KEY is missing, BingSearch.__init__ should raise the expected Exception."""
        # Ensure the environment is cleared of BING_API_KEY for the duration of the test
        with unittest.mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(Exception) as cm:
                # Instantiation triggers get_api_key in __init__
                BingSearch("test query")
            self.assertIn(
                "Bing API key not found. Please set the BING_API_KEY environment variable.",
                str(cm.exception)
            )
