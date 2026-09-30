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
        # Ensure EXA_API_KEY is not present in the environment
        original_value = os.environ.pop("EXA_API_KEY", None)
        try:
            # Create an ExaSearch instance without running __init__ to avoid external imports
            exa = ExaSearch.__new__(ExaSearch)
            with self.assertRaises(Exception) as cm:
                exa._retrieve_api_key()
            msg = str(cm.exception)
            # Verify the raised exception contains the expected guidance
            self.assertIn("Exa API key not found", msg)
            self.assertIn("EXA_API_KEY", msg)
            self.assertIn("https://exa.ai/", msg)
        finally:
            # Restore original environment state
            if original_value is not None:
                os.environ["EXA_API_KEY"] = original_value
