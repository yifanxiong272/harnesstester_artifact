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
        """Verify that when SERPER_EXCLUDE_SITES is not set (or empty) the method returns an empty list."""
        # Save original environment state
        orig_api = os.environ.get("SERPER_API_KEY")
        orig_exclude = os.environ.get("SERPER_EXCLUDE_SITES")
        try:
            # Ensure SERPER_EXCLUDE_SITES is not set (so os.getenv(..., "") yields "")
            os.environ.pop("SERPER_EXCLUDE_SITES", None)
            # Ensure an API key is present to avoid __init__ raising
            os.environ["SERPER_API_KEY"] = "dummy_key"

            # Instantiate without passing exclude_sites so _get_exclude_sites_from_env is used
            search = SerperSearch(query="example query", exclude_sites=None)

            # The internal method should return an empty list and the instance attribute should be []
            self.assertEqual(search._get_exclude_sites_from_env(), [])
            self.assertEqual(search.exclude_sites, [])
        finally:
            # Restore original environment
            if orig_api is None:
                os.environ.pop("SERPER_API_KEY", None)
            else:
                os.environ["SERPER_API_KEY"] = orig_api

            if orig_exclude is None:
                os.environ.pop("SERPER_EXCLUDE_SITES", None)
            else:
                os.environ["SERPER_EXCLUDE_SITES"] = orig_exclude
