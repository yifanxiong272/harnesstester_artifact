import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.searchapi.searchapi')
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
        """Ensure SearchApiSearch raises a clear exception when SEARCHAPI_API_KEY is missing"""
        # Ensure the environment does not contain the SEARCHAPI_API_KEY
        with patch.dict(os.environ, {}, clear=True):
            # Instantiating should attempt to read the env var and raise the expected Exception
            with self.assertRaisesRegex(Exception, r"SearchApi key not found\."):
                SearchApiSearch("dummy query")
