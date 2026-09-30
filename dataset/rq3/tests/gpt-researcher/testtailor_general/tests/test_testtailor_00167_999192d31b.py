import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.scraper.tavily_extract.tavily_extract')
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
        """When TAVILY_API_KEY is not set, get_api_key should raise the expected Exception."""
        # Ensure the environment variable is absent for this test, but restore it afterwards.
        previous = os.environ.pop("TAVILY_API_KEY", None)
        try:
            # Create an instance without calling __init__ to avoid importing external dependencies.
            instance = object.__new__(TavilyExtract)
            with self.assertRaisesRegex(
                Exception,
                "Tavily API key not found. Please set the TAVILY_API_KEY environment variable."
            ):
                instance.get_api_key()
        finally:
            if previous is not None:
                os.environ["TAVILY_API_KEY"] = previous
            else:
                os.environ.pop("TAVILY_API_KEY", None)
