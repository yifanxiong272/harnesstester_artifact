# file: gpt_researcher/actions/retriever.py:8-106
# asked: {"lines": [37, 39, 41, 43, 45, 47, 49, 51, 53, 55, 57, 59, 61, 63, 65, 67, 69, 71, 76, 77, 79, 80, 81, 83, 84, 85, 87, 88, 89, 91, 92, 93, 95, 96, 97, 99, 100, 101, 103, 105, 106], "branches": [[35, 37], [35, 41], [35, 45], [35, 49], [35, 53], [35, 57], [35, 61], [35, 65], [35, 69], [35, 77], [35, 81], [35, 85], [35, 89], [35, 93], [35, 97], [35, 101], [35, 106]]}
# gained: {"lines": [37, 39, 41, 43, 45, 47, 49, 51, 53, 55, 57, 59, 61, 63, 65, 67, 69, 71, 76, 77, 79, 80, 81, 83, 84, 85, 87, 88, 89, 91, 92, 93, 95, 96, 97, 99, 100, 101, 103, 105, 106], "branches": [[35, 37], [35, 41], [35, 45], [35, 49], [35, 53], [35, 57], [35, 61], [35, 65], [35, 69], [35, 77], [35, 81], [35, 85], [35, 89], [35, 93], [35, 97], [35, 101], [35, 106]]}

import importlib.util
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture
def load_original_retriever_module(monkeypatch):
    """
    Locate the original gpt_researcher/actions/retriever.py file in the repo,
    load it as the module named 'gpt_researcher.actions.retriever', and ensure
    a fake 'gpt_researcher.retrievers' module with all expected classes exists
    in sys.modules so the dynamic imports inside get_retriever succeed.

    Yields the loaded module.
    """
    # Search upwards from this file for the repository directory containing gpt_researcher/actions/retriever.py
    current = Path(__file__).resolve().parent
    target_path = None
    for p in [current] + list(current.parents):
        candidate = p / "gpt_researcher" / "actions" / "retriever.py"
        if candidate.exists():
            target_path = candidate
            break

    if target_path is None:
        pytest.skip("Could not find gpt_researcher/actions/retriever.py in repository tree")

    # Prepare package modules in sys.modules
    pkg_name = "gpt_researcher"
    actions_pkg_name = f"{pkg_name}.actions"
    retrievers_mod_name = f"{pkg_name}.retrievers"
    retriever_mod_name = f"{actions_pkg_name}.retriever"

    # Create package modules (mark as packages by giving __path__)
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [str(target_path.parent.parent)]  # gpt_researcher directory
    monkeypatch.setitem(sys.modules, pkg_name, pkg)

    actions_pkg = types.ModuleType(actions_pkg_name)
    actions_pkg.__path__ = [str(target_path.parent)]  # actions directory
    monkeypatch.setitem(sys.modules, actions_pkg_name, actions_pkg)

    # Create fake retrievers module with all expected classes
    retrievers_mod = types.ModuleType(retrievers_mod_name)
    class_names = [
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
    for name in class_names:
        cls = type(name, (), {"__repr__": lambda self, n=name: f"<{n} dummy>"})
        setattr(retrievers_mod, name, cls)
    monkeypatch.setitem(sys.modules, retrievers_mod_name, retrievers_mod)

    # Load the original retriever.py as module named 'gpt_researcher.actions.retriever'
    spec = importlib.util.spec_from_file_location(retriever_mod_name, str(target_path))
    module = importlib.util.module_from_spec(spec)
    # Ensure sys.modules has the module entry before executing to allow intra-module imports
    monkeypatch.setitem(sys.modules, retriever_mod_name, module)
    # Execute the module
    spec.loader.exec_module(module)

    yield module


def test_get_retriever_all_branches(load_original_retriever_module):
    mod = load_original_retriever_module
    # All retriever names expected by the function
    cases = {
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

    for name, expected_classname in cases.items():
        cls = mod.get_retriever(name)
        assert isinstance(cls, type), f"Expected a class for retriever '{name}'"
        assert cls.__name__ == expected_classname, f"Retriever '{name}' returned {cls.__name__}, expected {expected_classname}"


def test_get_retriever_default_case(load_original_retriever_module):
    mod = load_original_retriever_module
    # Should return None for unknown retriever names
    assert mod.get_retriever("this_retriever_does_not_exist") is None
