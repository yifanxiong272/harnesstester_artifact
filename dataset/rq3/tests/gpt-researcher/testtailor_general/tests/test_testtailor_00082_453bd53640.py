import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.bocha.bocha')
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
        """Verify BoChaSearch __init__ sets query, query_domains, and reads BOCHA_API_KEY from environment."""
        # Ensure the environment variable is set for the initializer to read
        os.environ["BOCHA_API_KEY"] = "test-key"

        # Case 1: query_domains omitted -> should become None
        bs1 = BoChaSearch(query="my query")
        self.assertEqual(bs1.query, "my query")
        self.assertIsNone(bs1.query_domains)
        self.assertEqual(bs1.api_key, "test-key")

        # Case 2: query_domains provided -> should be kept as given
        domains = ["example.com"]
        bs2 = BoChaSearch(query="another query", query_domains=domains)
        self.assertEqual(bs2.query, "another query")
        self.assertEqual(bs2.query_domains, domains)
        self.assertEqual(bs2.api_key, "test-key")
