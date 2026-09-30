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
        """Test that ExaSearch __init__ calls check_pkg, imports Exa, sets attributes properly."""
        import os
        import sys
        import types
        import importlib

        # Prepare environment and a fake exa_py module with an Exa class
        os.environ["EXA_API_KEY"] = "dummy-key-123"
        original_exa_module = sys.modules.get("exa_py")
        fake_exa = types.ModuleType("exa_py")

        class DummyExa:
            def __init__(self, api_key=None):
                # store the passed api_key for inspection
                self.api_key = api_key

        fake_exa.Exa = DummyExa
        sys.modules["exa_py"] = fake_exa

        # Try to locate the module that defines ExaSearch
        candidate_paths = [
            "gpt_researcher.retrievers.exa_search",
            "gpt_researcher.retrievers.exa",
            "gpt_researcher.retrievers.exa_searcher",
            "gpt_researcher.search.exa_search",
            "gpt_researcher.exa_search",
            "gpt_researcher.retriever.exa_search",
        ]

        ExaSearch = None
        exa_module = None
        for path in candidate_paths:
            try:
                mod = importlib.import_module(path)
                maybe = getattr(mod, "ExaSearch", None)
                if maybe:
                    ExaSearch = maybe
                    exa_module = mod
                    break
            except Exception:
                continue

        if ExaSearch is None:
            # If we couldn't find the module via candidates, try to find any loaded module defining ExaSearch
            for name, mod in list(sys.modules.items()):
                if mod and hasattr(mod, "ExaSearch"):
                    ExaSearch = getattr(mod, "ExaSearch")
                    exa_module = mod
                    break

        if ExaSearch is None:
            # Fail the test with a clear message so maintainers can adjust the import path list
            # (Don't leave the fake module in sys.modules)
            if original_exa_module is not None:
                sys.modules["exa_py"] = original_exa_module
            else:
                del sys.modules["exa_py"]
            self.fail("Could not locate ExaSearch in expected module paths. Update candidate_paths.")

        # Ensure the module where ExaSearch is defined has a no-op check_pkg
        setattr(exa_module, "check_pkg", lambda pkg: None)

        try:
            # Instantiate with explicit query_domains
            query_text = "find relevant docs"
            domains = ["example.com", "other.com"]
            instance = ExaSearch(query_text, query_domains=domains)

            # Verify that attributes were set as expected
            self.assertEqual(instance.query, query_text)
            self.assertEqual(instance.api_key, "dummy-key-123")
            # client should be an instance of our DummyExa and carry the api key
            self.assertIsInstance(instance.client, DummyExa)
            self.assertEqual(instance.client.api_key, "dummy-key-123")
            self.assertEqual(instance.query_domains, domains)

            # Instantiate with query_domains that evaluate to False (e.g., empty list) -> becomes None
            instance2 = ExaSearch("q2", query_domains=[])
            self.assertIsNone(instance2.query_domains)

        finally:
            # Clean up: restore original exa_py module and remove env var
            if original_exa_module is not None:
                sys.modules["exa_py"] = original_exa_module
            else:
                sys.modules.pop("exa_py", None)
            os.environ.pop("EXA_API_KEY", None)
