import sys
from types import ModuleType
import importlib
import pytest

# Import the function under test. The function performs dynamic imports inside its body,
# so we create/insert a dummy package/module into sys.modules before calling it.
from gpt_researcher.actions.retriever import get_retriever


def _install_dummy_retrievers():
    """Install a dummy gpt_researcher.retrievers module with the expected class names.
    Returns a dict with:
      - "mod": the dummy module object
      - "backup": any previously installed sys.modules entries that were replaced
    """
    names = [
        "GoogleSearch",
        "SearxSearch",
        "SearchApiSearch",
        "SerpApiSearch",
        "SerperSearch",
        "Duckduckgo",
        "BingSearch",
        "BoChaSearch",
        "ArxivSearch",
        "TavilySearch",
        "ExaSearch",
        "SemanticScholarSearch",
        "PubMedCentralSearch",
        "CustomRetriever",
        "MCPRetriever",
        "XquikSearch",
        "OpenAlexSearch",
    ]

    backup = {}
    # Preserve any existing modules so we can restore them later
    for key in ("gpt_researcher", "gpt_researcher.retrievers"):
        if key in sys.modules:
            backup[key] = sys.modules[key]

    pkg = ModuleType("gpt_researcher")
    # mark as a package
    pkg.__path__ = []
    mod = ModuleType("gpt_researcher.retrievers")

    # Create simple unique dummy classes for each expected name.
    for nm in names:
        # use type() to create a class with a readable repr for debugging
        cls = type(nm, (), {"__repr__": (lambda self, n=nm: f"<{n} dummy>")})
        setattr(mod, nm, cls)

    # Install into sys.modules so the dynamic 'from gpt_researcher.retrievers import X' works
    sys.modules["gpt_researcher"] = pkg
    sys.modules["gpt_researcher.retrievers"] = mod

    return {"mod": mod, "backup": backup}


def _uninstall_dummy_retrievers(state):
    """Restore any modules replaced by _install_dummy_retrievers."""
    backup = state.get("backup", {})
    # Remove the dummy entries
    sys.modules.pop("gpt_researcher.retrievers", None)
    sys.modules.pop("gpt_researcher", None)
    # Restore backups
    for k, v in backup.items():
        sys.modules[k] = v


def test_get_retriever_all_round_012():
    """Verify that each supported retriever name returns the expected class object.

    This test installs a deterministic dummy module that exposes known class objects
    and asserts identity (is) to ensure get_retriever returns the exact class.
    """
    state = _install_dummy_retrievers()
    mod = state["mod"]

    try:
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
            "custom": "CustomRetriever",
            "mcp": "MCPRetriever",
            "xquik": "XquikSearch",
            "openalex": "OpenAlexSearch",
        }

        # For determinism, iterate over a sorted list of keys
        for key in sorted(mapping.keys()):
            expected_name = mapping[key]
            result = get_retriever(key)
            # The function is expected to return the class object object from the dummy module
            assert result is getattr(mod, expected_name), (
                f"for key={key!r} expected {expected_name} but got {result!r}"
            )
    finally:
        _uninstall_dummy_retrievers(state)


def test_get_retriever_unknown_round_012():
    """Unknown retriever names should return None."""
    state = _install_dummy_retrievers()
    try:
        # Strings that are not exact matches should return None
        assert get_retriever("not-a-real-retriever") is None
        # Different casing does not match; ensure exact-match semantics
        assert get_retriever("Google") is None
        assert get_retriever("") is None
    finally:
        _uninstall_dummy_retrievers(state)
