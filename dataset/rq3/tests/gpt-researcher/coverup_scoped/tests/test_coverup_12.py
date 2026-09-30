# file: gpt_researcher/actions/retriever.py:8-106
# asked: {"lines": [37, 39, 41, 43, 45, 47, 49, 51, 53, 55, 57, 59, 61, 63, 65, 67, 69, 71, 76, 77, 79, 80, 81, 83, 84, 85, 87, 88, 89, 91, 92, 93, 95, 96, 97, 99, 100, 101, 103, 105, 106], "branches": [[35, 37], [35, 41], [35, 45], [35, 49], [35, 53], [35, 57], [35, 61], [35, 65], [35, 69], [35, 77], [35, 81], [35, 85], [35, 89], [35, 93], [35, 97], [35, 101], [35, 106]]}
# gained: {"lines": [37, 39, 41, 43, 45, 47, 49, 51, 53, 55, 57, 59, 61, 63, 65, 67, 69, 71, 76, 77, 79, 80, 81, 83, 84, 85, 87, 88, 89, 91, 92, 93, 95, 96, 97, 99, 100, 101, 103, 105, 106], "branches": [[35, 37], [35, 41], [35, 45], [35, 49], [35, 53], [35, 57], [35, 61], [35, 65], [35, 69], [35, 77], [35, 81], [35, 85], [35, 89], [35, 93], [35, 97], [35, 101], [35, 106]]}

import sys
import types
import pytest

from gpt_researcher.actions.retriever import get_retriever

RETRIEVER_ATTRS = {
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


@pytest.fixture
def fake_retrievers_module(monkeypatch):
    """
    Insert a fake gpt_researcher.retrievers module into sys.modules with
    attributes for all retriever classes referenced by get_retriever.
    Ensures cleanup via monkeypatch.
    """
    # Create package and submodule
    pkg = types.ModuleType("gpt_researcher")
    mod = types.ModuleType("gpt_researcher.retrievers")

    # Populate module with distinct class objects for each expected attribute
    created = {}
    for attr in RETRIEVER_ATTRS.values():
        # create a simple unique class for each attribute
        cls = type(attr, (object,), {})
        setattr(mod, attr, cls)
        created[attr] = cls

    # Ensure package points to submodule
    setattr(pkg, "retrievers", mod)

    # Insert into sys.modules so "from gpt_researcher.retrievers import X" works
    monkeypatch.setitem(sys.modules, "gpt_researcher", pkg)
    monkeypatch.setitem(sys.modules, "gpt_researcher.retrievers", mod)

    return created


@pytest.mark.parametrize("name,attr", list(RETRIEVER_ATTRS.items()))
def test_get_retriever_returns_expected_class(name, attr, fake_retrievers_module):
    # Call get_retriever and ensure it returns the exact class object from our fake module
    expected_class = fake_retrievers_module[attr]
    result = get_retriever(name)
    assert result is expected_class


def test_get_retriever_unknown_returns_none(fake_retrievers_module):
    # Unknown retriever should return None
    assert get_retriever("this_does_not_exist") is None
