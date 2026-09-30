import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.searx.searx')
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
        """Ensure get_searxng_url reads SEARX_URL and normalizes trailing slash."""
        # Preserve original environment
        original = os.environ.get("SEARX_URL")
        try:
            # Case 1: URL without trailing slash -> should add slash
            os.environ["SEARX_URL"] = "https://example.com"
            s = SearxSearch("test")
            self.assertEqual(s.base_url, "https://example.com/")

            # Case 2: URL already with trailing slash -> should remain unchanged
            os.environ["SEARX_URL"] = "https://example.org/"
            s2 = SearxSearch("another")
            self.assertEqual(s2.base_url, "https://example.org/")

        finally:
            # Restore original environment
            if original is None:
                os.environ.pop("SEARX_URL", None)
            else:
                os.environ["SEARX_URL"] = original
