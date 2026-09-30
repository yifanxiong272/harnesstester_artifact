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
        """Ensure get_api_key returns the SEARCHAPI_API_KEY from the environment."""
        # Preserve existing environment value
        previous = os.environ.get("SEARCHAPI_API_KEY")
        os.environ["SEARCHAPI_API_KEY"] = "test-key-123"
        try:
            searcher = SearchApiSearch(query="dummy query")
            # The __init__ calls get_api_key(), so api_key should be set from the env var
            self.assertEqual(searcher.api_key, "test-key-123")
            # Also verify calling get_api_key directly returns the same value
            self.assertEqual(searcher.get_api_key(), "test-key-123")
        finally:
            # Restore previous environment state
            if previous is None:
                os.environ.pop("SEARCHAPI_API_KEY", None)
            else:
                os.environ["SEARCHAPI_API_KEY"] = previous
