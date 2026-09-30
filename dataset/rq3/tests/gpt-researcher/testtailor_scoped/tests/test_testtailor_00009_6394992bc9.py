import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.actions.retriever')
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
        """Verify get_retriever returns the expected class for known retriever names and None otherwise."""
        # Locate the retrievers module where the classes are expected to live,
        # and locate the module that defines get_retriever (which might be a different module).
        import importlib
        import pkgutil
        import gpt_researcher

        # Ensure the canonical retrievers module object (where classes are imported from)
        retrievers_module = importlib.import_module("gpt_researcher.retrievers")

        # Search for the get_retriever function in submodules of the package (or the package itself)
        get_retriever = None
        # Check package itself first
        if hasattr(gpt_researcher, "get_retriever"):
            get_retriever = getattr(gpt_researcher, "get_retriever")
        else:
            # Iterate over submodules to find get_retriever
            for finder, name, ispkg in pkgutil.iter_modules(gpt_researcher.__path__):
                full_name = f"{gpt_researcher.__name__}.{name}"
                try:
                    mod = importlib.import_module(full_name)
                except Exception:
                    # skip modules that fail to import
                    continue
                if hasattr(mod, "get_retriever"):
                    get_retriever = getattr(mod, "get_retriever")
                    break

        if get_retriever is None:
            # As a last resort, check the retrievers module itself
            if hasattr(retrievers_module, "get_retriever"):
                get_retriever = getattr(retrievers_module, "get_retriever")

        # Fail the test if we couldn't find the function under test
        if get_retriever is None:
            self.fail("Could not locate get_retriever in the gpt_researcher package or its submodules")

        # Map retriever keys to the attribute names used in the match statement
        mapping = {
            "google": "GoogleSearch",
            "searx": "SearxSearch",
            "searchapi": "SearchApiSearch",
            "serpapi": "SerpApiSearch",
            "serper": "SerperSearch",
            "duckduckgo": "Duckduckgo",
            "bing": "BingSearch",
            "bocha": "BoChaSearch",
            "arxiv": "ArxivSearch",
            "tavily": "TavilySearch",
            "exa": "ExaSearch",
            "semantic_scholar": "SemanticScholarSearch",
            "pubmed_central": "PubMedCentralSearch",
            "openalex": "OpenAlexSearch",
            "custom": "CustomRetriever",
            "mcp": "MCPRetriever",
            "xquik": "XquikSearch",
        }

        # Preserve any existing attributes so we can restore them after the test
        originals = {}
        for attr in mapping.values():
            if hasattr(retrievers_module, attr):
                originals[attr] = getattr(retrievers_module, attr)

        try:
            # Inject dummy classes for each expected retriever class name into retrievers_module
            for attr in mapping.values():
                setattr(retrievers_module, attr, type(attr, (), {}))

            # Test that each retriever key returns the corresponding dummy class
            for key, attr in mapping.items():
                result = get_retriever(key)
                self.assertIs(result, getattr(retrievers_module, attr), f"Mismatch for key '{key}'")

            # Unknown retriever should return None
            self.assertIsNone(get_retriever("this_does_not_exist"))
        finally:
            # Restore original attributes (clean up)
            for attr, val in originals.items():
                setattr(retrievers_module, attr, val)
            # Remove injected attributes that were not originally present
            for attr in set(mapping.values()) - set(originals.keys()):
                if hasattr(retrievers_module, attr):
                    delattr(retrievers_module, attr)
