import types
import pytest

from backend.report_type.detailed_report import detailed_report as dr_mod
from backend.report_type.detailed_report.detailed_report import DetailedReport


class FakeGPTResearcher:
    """
    Lightweight fake replacement for GPTResearcher used in tests.
    It records the kwargs it was constructed with and exposes a mutable
    cfg object with attribute max_search_results_per_query to emulate
    the real object's expected shape.
    """

    def __init__(self, **kwargs):
        # record what parameters were passed in
        self.kwargs = kwargs
        # emulate a simple config object used by DetailedReport
        self.cfg = types.SimpleNamespace(max_search_results_per_query=None)


def test_init_without_optional_params_round_037(monkeypatch):
    """Verify __init__ sets defaults and does not inject MCP params when none provided."""
    # Patch the GPTResearcher symbol where the DetailedReport module resolves it
    monkeypatch.setattr(dr_mod, "GPTResearcher", FakeGPTResearcher)

    # Instantiate with headers=None and no mcp / no max_search_results
    report = DetailedReport(
        query="some query",
        report_type="type",
        report_source="source",
        source_urls=[],
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

    # header defaulting behavior (line 39)
    assert isinstance(report.headers, dict)
    assert report.headers == {}

    # attributes should reflect constructor arguments (lines 29-41)
    assert report.query == "some query"
    assert report.report_type == "type"
    assert report.report_source == "source"
    assert report.source_urls == []

    # research_id was generated via the instance method (line 44)
    assert isinstance(report.research_id, str)
    # calling the generator again should produce the same id (determinism)
    assert report.research_id == report._generate_research_id("some query")

    # Ensure GPTResearcher was created and did not receive MCP params (lines 62-65)
    gr = report.gpt_researcher
    assert isinstance(gr, FakeGPTResearcher)
    assert "mcp_configs" not in gr.kwargs
    assert "mcp_strategy" not in gr.kwargs

    # max_search_results not provided, so the cfg attribute should remain None (line 70-71)
    assert getattr(gr.cfg, "max_search_results_per_query") is None

    # With empty source_urls, global_urls should be an empty set (lines 75-76)
    assert report.global_urls == set()


def test_init_with_mcp_and_max_search_round_037(monkeypatch):
    """Verify MCP params get passed to GPTResearcher and max_search_results is applied."""
    # Patch the GPTResearcher symbol in the module under test
    monkeypatch.setattr(dr_mod, "GPTResearcher", FakeGPTResearcher)

    mcp_cfg = {"param": 42}
    mcp_strat = "custom_strategy"
    max_search = "7"  # string on purpose to test int conversion
    src_urls = ["https://a.example/", "https://b.example/"]
    hdrs = {"Auth": "token"}

    report = DetailedReport(
        query="another q",
        report_type="detailed",
        report_source="src",
        source_urls=src_urls,
        document_urls=["doc1"],
        query_domains=["example.com"],
        config_path="/tmp/config",
        tone="neutral",
        websocket=None,
        subtopics=[],
        headers=hdrs,
        complement_source_urls=True,
        mcp_configs=mcp_cfg,
        mcp_strategy=mcp_strat,
        max_search_results=max_search,
    )

    # GPTResearcher should have been constructed with MCP params included (lines 62-65)
    gr = report.gpt_researcher
    assert isinstance(gr, FakeGPTResearcher)
    # ensure the kwargs passed downstream contain the MCP keys and their exact values
    assert gr.kwargs.get("mcp_configs") is mcp_cfg
    assert gr.kwargs.get("mcp_strategy") == mcp_strat

    # max_search_results should have been converted to int and applied to the cfg (lines 70-71)
    assert gr.cfg.max_search_results_per_query == int(max_search)

    # headers passed by user should be preserved
    assert report.headers is hdrs

    # global_urls should contain the provided source URLs
    assert report.global_urls == set(src_urls)

    # some other lightweight checks on state initialized in __init__
    assert isinstance(report.existing_headers, list)
    assert report.existing_headers == []
    assert isinstance(report.global_context, list)
    assert report.global_context == []
    assert isinstance(report.global_written_sections, list)
    assert report.global_written_sections == []
