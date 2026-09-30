import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.exa.exa')
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
        """Missing EXA_API_KEY should raise the expected Exception from _retrieve_api_key."""
        # Ensure environment has no EXA_API_KEY
        with patch.dict(os.environ, {}, clear=True):
            # Create an ExaSearch instance without calling __init__ to avoid external imports/side effects
            exa = ExaSearch.__new__(ExaSearch)
            # Expect the specific Exception when EXA_API_KEY is missing
            with self.assertRaisesRegex(Exception, r"Exa API key not found"):
                exa._retrieve_api_key()
