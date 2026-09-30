import sys
import types
from gpt_researcher.actions.retriever import get_retriever


def _install_fake_retrievers(class_names):
    """Install a fake gpt_researcher.retrievers module into sys.modules.

    class_names: iterable of class name strings to create as simple sentinel classes
    Returns a dict mapping class name -> class object installed in the fake module.
    """
    mod = types.ModuleType("gpt_researcher.retrievers")
    created = {}
    for name in class_names:
        cls = type(name, (), {})
        setattr(mod, name, cls)
        created[name] = cls
    # Put the fake module where get_retriever will import it from
    sys.modules["gpt_researcher.retrievers"] = mod
    return created


def _remove_fake_retrievers():
    """Remove fake retrievers module if present to avoid leaking state between tests."""
    sys.modules.pop("gpt_researcher.retrievers", None)


def test_each_known_retriever_returns_expected_class_round_012():
    # Map of retriever input -> expected class name (as imported from gpt_researcher.retrievers)
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

    # Install fake module with all expected class names
    created = _install_fake_retrievers(mapping.values())
    try:
        # For each retriever key, ensure get_retriever returns the exact sentinel class object
        for retriever_key, class_name in mapping.items():
            got = get_retriever(retriever_key)
            assert got is created[class_name], (
                f"get_retriever({retriever_key!r}) returned {got!r}, expected {created[class_name]!r}"
            )
    finally:
        _remove_fake_retrievers()


def test_unknown_retriever_returns_none_round_012():
    # Ensure fake module is present but the unknown key should return None
    created = _install_fake_retrievers([
        "GoogleSearch",
        "SearxSearch",
    ])
    try:
        # a name not handled by the match-case should return None
        assert get_retriever("nonexistent_retriever") is None

        # even if the fake module has unrelated attributes, unknown input still yields None
        assert get_retriever("") is None
        assert get_retriever("unknown") is None
    finally:
        _remove_fake_retrievers()


def test_partial_module_presence_still_returns_expected_round_012():
    # Install a module that only exposes a subset of retrievers and ensure those work
    created = _install_fake_retrievers([
        "GoogleSearch",
        "Duckduckgo",
        "BingSearch",
    ])
    try:
        assert get_retriever("google") is created["GoogleSearch"]
        assert get_retriever("duckduckgo") is created["Duckduckgo"]
        assert get_retriever("bing") is created["BingSearch"]
        # An exposed class name that isn't mapped to an input should not affect other inputs
        assert get_retriever("serpapi") is None
    finally:
        _remove_fake_retrievers()
