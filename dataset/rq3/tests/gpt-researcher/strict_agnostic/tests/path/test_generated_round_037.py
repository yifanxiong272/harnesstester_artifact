import types
import importlib

import pytest

# Deterministic dummy to replace the real GPTResearcher used by the module under test.
class DummyGPTResearcher:
    def __init__(self, **kwargs):
        # capture the kwargs used to construct the researcher for assertions
        self.passed_kwargs = kwargs
        # provide a simple cfg object with the expected attribute
        self.cfg = types.SimpleNamespace(max_search_results_per_query=None)


def _patch_module(monkeypatch):
    """Import the target module and patch out external dependencies deterministically."""
    mod = importlib.import_module("backend.report_type.detailed_report.detailed_report")
    # Replace the GPTResearcher class with the dummy implementation
    monkeypatch.setattr(mod, "GPTResearcher", DummyGPTResearcher)
    # Force the research id generation to be deterministic
    monkeypatch.setattr(mod.DetailedReport, "_generate_research_id", lambda self, q: "fixed-id")
    return mod


def test_init_with_mcp_and_max_search_results_round_037(monkeypatch):
    """
    Exercise the branches where mcp_configs and mcp_strategy are provided and
    max_search_results is set. Assert that the GPTResearcher was constructed
    with the expected keys and that max_search_results_per_query is applied.
    """
    mod = _patch_module(monkeypatch)
    DetailedReport = mod.DetailedReport

    # Prepare inputs that trigger the 'true' branches for the optional params
    query = "some query"
    report_type = "rt"
    report_source = "rs"
    source_urls = ["https://example.com/a"]
    document_urls = ["doc1"]
    query_domains = ["example.com"]
    config_path = "/tmp/config"
    tone = "neutral"
    websocket = None
    subtopics = []
    headers = {"Authorization": "Bearer token"}
    complement_source_urls = True
    mcp_configs = {"conf": 1}
    mcp_strategy = "strategy-x"
    max_search_results = 5

    dr = DetailedReport(
        query,
        report_type,
        report_source,
        source_urls,
        document_urls,
        query_domains,
        config_path,
        tone,
        websocket,
        subtopics,
        headers,
        complement_source_urls,
        mcp_configs,
        mcp_strategy,
        max_search_results,
    )

    # Basic attribute assignments from the init
    assert dr.query == query
    assert dr.report_type == report_type
    assert dr.report_source == report_source
    assert dr.source_urls == source_urls
    assert dr.document_urls == document_urls
    assert dr.query_domains == query_domains
    assert dr.config_path == config_path
    assert dr.tone == tone
    assert dr.websocket is websocket
    assert dr.subtopics == subtopics
    # headers should be used as provided
    assert dr.headers == headers
    assert dr.complement_source_urls is True

    # The research id must be the deterministic patched value
    assert dr.research_id == "fixed-id"

    # The patched GPTResearcher should have been constructed and stored
    assert isinstance(dr.gpt_researcher, DummyGPTResearcher)
    # Ensure mcp keys are present in the construction kwargs
    assert "mcp_configs" in dr.gpt_researcher.passed_kwargs
    assert dr.gpt_researcher.passed_kwargs["mcp_configs"] == mcp_configs
    assert "mcp_strategy" in dr.gpt_researcher.passed_kwargs
    assert dr.gpt_researcher.passed_kwargs["mcp_strategy"] == mcp_strategy

    # The max_search_results override should have been applied to the cfg
    assert dr.gpt_researcher.cfg.max_search_results_per_query == int(max_search_results)

    # Some global collections initialized in __init__
    assert isinstance(dr.existing_headers, list)
    assert isinstance(dr.global_context, list)
    assert isinstance(dr.global_written_sections, list)
    assert isinstance(dr.global_urls, set)
    # global_urls should reflect provided source_urls
    assert dr.global_urls == set(source_urls)


def test_init_without_optional_params_round_037(monkeypatch):
    """
    Exercise the branches where optional parameters mcp_configs, mcp_strategy,
    and max_search_results are left as None. This verifies the 'false' branches
    and default behaviors such as headers defaulting to an empty dict and
    global_urls becoming an empty set when source_urls is empty.
    """
    mod = _patch_module(monkeypatch)
    DetailedReport = mod.DetailedReport

    # Provide minimal inputs and leave optional MCP and max_search_results as None
    query = "q2"
    report_type = "rt2"
    report_source = "rs2"
    source_urls = []  # empty to trigger the else branch for global_urls
    document_urls = []
    query_domains = []
    config_path = None
    tone = ""
    websocket = None
    subtopics = []
    headers = None  # should default to {}
    complement_source_urls = False
    mcp_configs = None
    mcp_strategy = None
    max_search_results = None

    dr = DetailedReport(
        query,
        report_type,
        report_source,
        source_urls,
        document_urls,
        query_domains,
        config_path,
        tone,
        websocket,
        subtopics,
        headers,
        complement_source_urls,
        mcp_configs,
        mcp_strategy,
        max_search_results,
    )

    # Attributes set correctly
    assert dr.query == query
    assert dr.report_type == report_type
    # headers default to an empty dict when None
    assert dr.headers == {}

    # research_id deterministic
    assert dr.research_id == "fixed-id"

    # gpt_researcher created and did not receive mcp keys
    assert isinstance(dr.gpt_researcher, DummyGPTResearcher)
    assert "mcp_configs" not in dr.gpt_researcher.passed_kwargs
    assert "mcp_strategy" not in dr.gpt_researcher.passed_kwargs

    # Since max_search_results was None, cfg.max_search_results_per_query should remain None
    assert dr.gpt_researcher.cfg.max_search_results_per_query is None

    # global_urls should be an empty set because source_urls was empty
    assert dr.global_urls == set()
