# file: backend/report_type/detailed_report/detailed_report.py:11-76
# asked: {"lines": [29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 44, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 62, 63, 64, 65, 67, 70, 71, 72, 73, 74, 75, 76], "branches": [[62, 63], [62, 64], [64, 65], [64, 67], [70, 71], [70, 72]]}
# gained: {"lines": [29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 44, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 62, 63, 64, 65, 67, 70, 71, 72, 73, 74, 75, 76], "branches": [[62, 63], [62, 64], [64, 65], [64, 67], [70, 71], [70, 72]]}

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def detailed_report_module():
    # Find the detailed_report.py file in the repository
    repo_root = Path.cwd()
    candidates = list(repo_root.rglob("detailed_report.py"))

    chosen = None
    for p in candidates:
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if "class DetailedReport" in text and "self._generate_research_id" in text:
            chosen = p
            break

    if chosen is None:
        raise FileNotFoundError(
            "Could not locate detailed_report.py containing DetailedReport class."
        )

    # Load the module from the chosen file path
    spec = importlib.util.spec_from_file_location("tested_detailed_report", chosen)
    module = importlib.util.module_from_spec(spec)
    loader = spec.loader
    assert loader is not None
    loader.exec_module(module)
    # Ensure accessible by tests
    sys.modules["tested_detailed_report"] = module
    return module


def test_constructor_without_mcp_and_without_max(monkeypatch, detailed_report_module):
    module = detailed_report_module

    # Prepare a fake GPTResearcher to capture initialization params
    class FakeGPTResearcher:
        def __init__(self, **kwargs):
            # store received kwargs for inspection
            self.received_kwargs = kwargs
            # provide a cfg object with a mutable attribute that might be changed
            self.cfg = SimpleNamespace(max_search_results_per_query=5)

    # Patch the GPTResearcher used in the DetailedReport module
    monkeypatch.setattr(module, "GPTResearcher", FakeGPTResearcher)

    DetailedReport = module.DetailedReport

    # Inputs for constructor
    query = "test query"
    report_type = "some_type"
    report_source = "web"
    source_urls = ["https://a.example", "https://b.example"]
    document_urls = ["doc1"]
    query_domains = ["example.com"]
    config_path = "/tmp/config"
    tone = "formal"
    websocket = None
    subtopics = [{"title": "st1"}]
    headers = None  # should default to {}
    complement_source_urls = True

    dr = DetailedReport(
        query=query,
        report_type=report_type,
        report_source=report_source,
        source_urls=source_urls,
        document_urls=document_urls,
        query_domains=query_domains,
        config_path=config_path,
        tone=tone,
        websocket=websocket,
        subtopics=subtopics,
        headers=headers,
        complement_source_urls=complement_source_urls,
        mcp_configs=None,
        mcp_strategy=None,
        max_search_results=None,
    )

    # Ensure attributes set correctly
    assert dr.query == query
    assert dr.report_type == report_type
    assert dr.report_source == report_source
    assert dr.source_urls == source_urls
    assert dr.document_urls == document_urls
    assert dr.query_domains == query_domains
    assert dr.config_path == config_path
    assert dr.tone == tone
    assert dr.websocket == websocket
    assert dr.subtopics == subtopics
    # headers was None -> should become {}
    assert dr.headers == {}
    assert dr.complement_source_urls is True

    # research_id should be a non-empty string
    assert isinstance(dr.research_id, str) and len(dr.research_id) > 0

    # Check that the GPTResearcher was instantiated and received expected params.
    assert hasattr(dr, "gpt_researcher")
    received = dr.gpt_researcher.received_kwargs
    # The module always sets report_type to 'research_report' for GPTResearcher params
    assert received["report_type"] == "research_report"
    # Other values should be forwarded
    assert received["query"] == query
    assert received["report_source"] == report_source
    assert received["source_urls"] == source_urls
    assert received["document_urls"] == document_urls
    assert received["query_domains"] == query_domains
    assert received["config_path"] == config_path
    assert received["tone"] == tone
    assert received["websocket"] == websocket
    # headers forwarded as empty dict
    assert received["headers"] == {}

    # Since mcp_configs and mcp_strategy were not provided, they should not be in kwargs
    assert "mcp_configs" not in received
    assert "mcp_strategy" not in received

    # Since max_search_results was None, cfg should remain as the Fake's default
    assert dr.gpt_researcher.cfg.max_search_results_per_query == 5

    # Check post-init lists/sets
    assert dr.existing_headers == []
    assert dr.global_context == []
    assert dr.global_written_sections == []
    # global_urls should be set to set(source_urls)
    assert dr.global_urls == set(source_urls)


def test_constructor_with_mcp_and_with_max(monkeypatch, detailed_report_module):
    module = detailed_report_module

    # Fake GPTResearcher that allows mutation of cfg
    class FakeGPTResearcher:
        def __init__(self, **kwargs):
            self.received_kwargs = kwargs
            # start with a sentinel value; constructor should be able to have attribute mutated
            self.cfg = SimpleNamespace(max_search_results_per_query=0)

    monkeypatch.setattr(module, "GPTResearcher", FakeGPTResearcher)
    DetailedReport = module.DetailedReport

    # Provide empty source_urls to exercise the else branch for global_urls initialization
    dr = DetailedReport(
        query="another query",
        report_type="rt",
        report_source="api",
        source_urls=[],
        document_urls=[],
        query_domains=[],
        config_path=None,
        tone="casual",
        websocket=None,
        subtopics=[],
        headers={"A": "B"},
        complement_source_urls=False,
        mcp_configs={"foo": "bar"},
        mcp_strategy="my_strategy",
        max_search_results="42",
    )

    # Ensure provided headers are preserved (not overwritten)
    assert dr.headers == {"A": "B"}

    # Check that mcp params were forwarded to GPTResearcher
    received = dr.gpt_researcher.received_kwargs
    assert received["mcp_configs"] == {"foo": "bar"}
    assert received["mcp_strategy"] == "my_strategy"

    # max_search_results was provided (as string), code should set cfg.max_search_results_per_query
    # to int(max_search_results)
    assert dr.gpt_researcher.cfg.max_search_results_per_query == 42

    # global_urls should be empty set when source_urls is falsy/empty
    assert dr.global_urls == set()
