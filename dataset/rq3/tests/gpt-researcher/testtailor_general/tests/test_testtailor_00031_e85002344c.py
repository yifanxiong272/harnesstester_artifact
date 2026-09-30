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
        """Find and call the project's real get_retriever, ensure it maps names to classes and returns None for unknown."""
        import importlib
        import pkgutil
        import sys
        import types

        # Import the package
        pkg = importlib.import_module("gpt_researcher")

        # Discover the module that actually defines get_retriever by scanning submodules
        get_retriever = None
        for finder, name, ispkg in pkgutil.iter_modules(pkg.__path__):
            full_name = f"{pkg.__name__}.{name}"
            try:
                mod = importlib.import_module(full_name)
            except Exception:
                continue
            if hasattr(mod, "get_retriever"):
                get_retriever = getattr(mod, "get_retriever")
                break

        # Also check the package root as fallback
        if get_retriever is None and hasattr(pkg, "get_retriever"):
            get_retriever = getattr(pkg, "get_retriever")

        self.assertIsNotNone(get_retriever, "Could not locate get_retriever in the package modules")

        # Ensure the retrievers module exists so internal imports inside get_retriever succeed
        try:
            retrievers_mod = importlib.import_module("gpt_researcher.retrievers")
        except Exception:
            retrievers_mod = types.ModuleType("gpt_researcher.retrievers")
            sys.modules["gpt_researcher.retrievers"] = retrievers_mod

        # Provide dummy classes expected by get_retriever
        class_map = {
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
            "custom": "CustomRetriever",
            "mcp": "MCPRetriever",
            "xquik": "XquikSearch",
            "openalex": "OpenAlexSearch",
        }

        # Attach classes if not present
        for cls_name in set(class_map.values()):
            if not hasattr(retrievers_mod, cls_name):
                setattr(retrievers_mod, cls_name, type(cls_name, (), {}))

        # Now test that get_retriever returns the exact classes we attached
        for key, cls_name in class_map.items():
            expected = getattr(retrievers_mod, cls_name)
            actual = get_retriever(key)
            self.assertIs(actual, expected, f"get_retriever({key!r}) did not return the expected class")

        # Unknown retriever should return None
        self.assertIsNone(get_retriever("this_retriever_does_not_exist_12345"))
