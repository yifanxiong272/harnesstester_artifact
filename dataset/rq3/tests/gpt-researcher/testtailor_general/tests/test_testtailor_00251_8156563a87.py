import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.scraper.firecrawl.firecrawl')
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
        """get_api_key returns the value from FIRECRAWL_API_KEY environment variable"""
        test_key = "test-key-123"
        prev = os.environ.get("FIRECRAWL_API_KEY")
        os.environ["FIRECRAWL_API_KEY"] = test_key
        try:
            # Create instance without calling __init__ to avoid side effects
            fc = FireCrawl.__new__(FireCrawl)
            result = fc.get_api_key()
            self.assertEqual(result, test_key)
        finally:
            # Restore previous environment state
            if prev is None:
                del os.environ["FIRECRAWL_API_KEY"]
            else:
                os.environ["FIRECRAWL_API_KEY"] = prev
