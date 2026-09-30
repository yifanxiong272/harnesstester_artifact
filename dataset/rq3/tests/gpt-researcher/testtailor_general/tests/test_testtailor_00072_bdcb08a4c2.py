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
        """Test ExaSearch __init__ sets up query, api_key, client, and query_domains correctly."""
        # Obtain modules via __import__ to avoid top-level import statements
        sys = __import__("sys")
        types = __import__("types")
        os = __import__("os")

        original_exa = sys.modules.get("exa_py")
        try:
            # Ensure API key available
            os.environ["EXA_API_KEY"] = "test_api_key_123"

            # Create a fake exa_py module with an Exa class
            fake_exa = types.ModuleType("exa_py")

            class FakeExa:
                def __init__(self, api_key=None):
                    # record the api_key passed for verification
                    self.api_key = api_key

            fake_exa.Exa = FakeExa
            sys.modules["exa_py"] = fake_exa

            # Ensure the module defining ExaSearch has a no-op check_pkg function
            exa_module = sys.modules[ExaSearch.__module__]
            setattr(exa_module, "check_pkg", lambda pkg: None)

            # Case 1: provide query_domains
            search_obj = ExaSearch(query="my query", query_domains=["example.com"])
            self.assertEqual(search_obj.query, "my query")
            self.assertEqual(search_obj.api_key, "test_api_key_123")
            # client should be instance of our FakeExa and have received the api_key
            self.assertIsInstance(search_obj.client, FakeExa)
            self.assertEqual(search_obj.client.api_key, "test_api_key_123")
            self.assertEqual(search_obj.query_domains, ["example.com"])

            # Case 2: no query_domains provided -> should be None
            search_obj2 = ExaSearch(query="another query")
            self.assertEqual(search_obj2.query, "another query")
            self.assertIsInstance(search_obj2.client, FakeExa)
            self.assertEqual(search_obj2.query_domains, None)
        finally:
            # Restore any original exa_py module
            if original_exa is not None:
                sys.modules["exa_py"] = original_exa
            else:
                sys.modules.pop("exa_py", None)
            # Clean up environment variable
            os.environ.pop("EXA_API_KEY", None)
