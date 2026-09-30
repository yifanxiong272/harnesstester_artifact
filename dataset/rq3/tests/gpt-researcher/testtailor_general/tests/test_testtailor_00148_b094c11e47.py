import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.serpapi.serpapi')
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
        """When SERPAPI_API_KEY is not set, SerpApiSearch should raise a clear Exception."""
        # Ensure environment has no SERPAPI_API_KEY
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(Exception, "SerpApi API key not found"):
                # Instantiation triggers get_api_key in __init__
                SerpApiSearch(query="test query")
