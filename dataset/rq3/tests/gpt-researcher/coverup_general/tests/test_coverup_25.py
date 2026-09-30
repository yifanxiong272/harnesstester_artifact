# file: backend/report_type/detailed_report/detailed_report.py:11-76
# asked: {"lines": [29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 44, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 62, 63, 64, 65, 67, 70, 71, 72, 73, 74, 75, 76], "branches": [[62, 63], [62, 64], [64, 65], [64, 67], [70, 71], [70, 72]]}
# gained: {"lines": [29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 44, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 62, 63, 64, 65, 67, 70, 71, 72, 73, 74, 75, 76], "branches": [[62, 63], [62, 64], [64, 65], [64, 67], [70, 71], [70, 72]]}

import pytest
from types import SimpleNamespace

import backend.report_type.detailed_report.detailed_report as dr_mod


class FakeGPTResearcher:
    def __init__(self, **kwargs):
        # store received kwargs for assertions
        self.kwargs = kwargs
        # Provide a cfg object with attribute max_search_results_per_query that can be modified
        self.cfg = SimpleNamespace(max_search_results_per_query=0)


def test_init_defaults(monkeypatch):
    """
    Test DetailedReport.__init__ with default/None parameters to cover branches
    where mcp_configs and mcp_strategy are not provided and source_urls is empty.
    """
    # Patch GPTResearcher used in DetailedReport to avoid heavy initialization
    monkeypatch.setattr(dr_mod, "GPTResearcher", FakeGPTResearcher)

    # Instantiate with minimal params; headers left as None to exercise headers or {}
    dr = dr_mod.DetailedReport(
        query="test query",
        report_type="type_a",
        report_source="web",
        source_urls=[],  # explicit empty to exercise global_urls empty branch
        document_urls=[],
        query_domains=[],
        config_path=None,
        tone="",
        websocket=None,
        subtopics=[],
        headers=None,
        complement_source_urls=False,
        mcp_configs=None,
        mcp_strategy=None,
        max_search_results=None,
    )

    # Basic attributes set correctly
    assert dr.query == "test query"
    assert dr.report_type == "type_a"
    assert dr.report_source == "web"

    # When headers is None, DetailedReport should set headers to {}
    assert dr.headers == {}
    # existing_headers initialized empty
    assert dr.existing_headers == []
    assert dr.global_context == []
    assert dr.global_written_sections == []
    # global_urls should be empty set when source_urls empty
    assert dr.global_urls == set()

    # research_id should be a non-empty string and start with expected prefix
    assert isinstance(dr.research_id, str)
    assert dr.research_id.startswith("detailed_")
    assert len(dr.research_id) > len("detailed_")

    # Ensure GPTResearcher was constructed and stored
    assert isinstance(dr.gpt_researcher, FakeGPTResearcher)
    # And that the kwargs passed include the expected mapping keys
    expected_keys = {
        "query",
        "query_domains",
        "report_type",
        "report_source",
        "source_urls",
        "document_urls",
        "config_path",
        "tone",
        "websocket",
        "headers",
        "complement_source_urls",
    }
    assert expected_keys.issubset(set(dr.gpt_researcher.kwargs.keys()))
    # Since mcp_configs/mcp_strategy not provided, they should not be in kwargs
    assert "mcp_configs" not in dr.gpt_researcher.kwargs
    assert "mcp_strategy" not in dr.gpt_researcher.kwargs
    # max_search_results not provided so cfg should remain default (0)
    assert dr.gpt_researcher.cfg.max_search_results_per_query == 0


def test_init_with_mcp_and_sources_and_max_search_results(monkeypatch):
    """
    Test DetailedReport.__init__ with mcp_configs, mcp_strategy, non-empty source_urls,
    provided headers, complement_source_urls True, and max_search_results provided.
    This exercises the branches that add MCP parameters and that set cfg.max_search_results_per_query.
    """
    monkeypatch.setattr(dr_mod, "GPTResearcher", FakeGPTResearcher)

    source_urls = ["https://example.com/a", "https://example.com/b"]
    headers = {"Authorization": "Bearer token"}
    mcp_configs = [{"name": "mcp1", "command": "run"}]
    mcp_strategy = "fast"

    dr = dr_mod.DetailedReport(
        query="another query",
        report_type="type_b",
        report_source="local",
        source_urls=source_urls,
        document_urls=["doc1"],
        query_domains=["example.com"],
        config_path="/tmp/config",
        tone="casual",
        websocket=None,
        subtopics=[{"title": "s1"}],
        headers=headers,
        complement_source_urls=True,
        mcp_configs=mcp_configs,
        mcp_strategy=mcp_strategy,
        max_search_results=5,
    )

    # Attributes reflect inputs
    assert dr.query == "another query"
    assert dr.report_type == "type_b"
    assert dr.report_source == "local"
    assert dr.headers == headers
    assert dr.complement_source_urls is True

    # global_urls should be set from provided source_urls
    assert dr.global_urls == set(source_urls)

    # research_id should be a non-empty string and start with expected prefix
    assert isinstance(dr.research_id, str)
    assert dr.research_id.startswith("detailed_")

    # GPTResearcher was instantiated and received MCP parameters in kwargs
    assert isinstance(dr.gpt_researcher, FakeGPTResearcher)
    assert dr.gpt_researcher.kwargs.get("mcp_configs") == mcp_configs
    assert dr.gpt_researcher.kwargs.get("mcp_strategy") == mcp_strategy

    # max_search_results should have been applied to the gpt_researcher.cfg
    assert dr.gpt_researcher.cfg.max_search_results_per_query == 5

    # Ensure other passed parameters are present in the underlying GPTResearcher kwargs
    assert dr.gpt_researcher.kwargs["query"] == "another query"
    assert dr.gpt_researcher.kwargs["source_urls"] == source_urls
    assert dr.gpt_researcher.kwargs["headers"] == headers
