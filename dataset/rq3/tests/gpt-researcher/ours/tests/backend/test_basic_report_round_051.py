import types
import pytest

import importlib

# Import the module under test
module_path = 'backend.report_type.basic_report.basic_report'
br_mod = importlib.import_module(module_path)


class FakeGPTResearcher:
    """A deterministic stand-in for the real GPTResearcher used in BasicReport.__init__.

    It records the kwargs it was constructed with and exposes a cfg object
    with a mutable max_search_results_per_query attribute so tests can
    observe side effects from BasicReport.__init__.
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        # mirror the real attribute used by BasicReport for max_search_results_per_query
        self.cfg = types.SimpleNamespace(max_search_results_per_query=None)


def make_dummy_ws():
    """Return a lightweight dummy object to satisfy the websocket parameter.

    BasicReport only stores the websocket value, so any object suffices.
    """
    return object()


def test_init_with_all_optionals_round_051(monkeypatch):
    # Patch GPTResearcher used by the module to avoid any external calls
    monkeypatch.setattr(br_mod, 'GPTResearcher', FakeGPTResearcher)
    # Patch _generate_research_id to make it deterministic
    monkeypatch.setattr(br_mod.BasicReport, '_generate_research_id', lambda self, q: 'fixed-id')

    br = br_mod.BasicReport(
        query='search-term',
        query_domains=['example.com'],
        report_type='typeA',
        report_source='sourceX',
        source_urls=['http://a'],
        document_urls=['http://doc'],
        tone='neutral',
        config_path='/tmp/config',
        websocket=make_dummy_ws(),
        headers=None,  # exercise headers defaulting to {}
        mcp_configs={'provider': 'mock'},
        mcp_strategy='best-effort',
        max_search_results='7',  # string to ensure int conversion path
    )

    # Basic attribute assignments
    assert br.query == 'search-term'
    assert br.query_domains == ['example.com']
    assert br.report_type == 'typeA'
    assert br.report_source == 'sourceX'
    assert br.source_urls == ['http://a']
    assert br.document_urls == ['http://doc']
    assert br.tone == 'neutral'
    assert br.config_path == '/tmp/config'

    # headers was None so it should default to an empty dict
    assert isinstance(br.headers, dict) and br.headers == {}

    # research_id must be the patched deterministic value
    assert br.research_id == 'fixed-id'

    # gpt_researcher must be an instance of the fake researcher and must have
    # received the optional MCP params in its constructor kwargs
    assert isinstance(br.gpt_researcher, FakeGPTResearcher)
    assert br.gpt_researcher.kwargs.get('mcp_configs') == {'provider': 'mock'}
    assert br.gpt_researcher.kwargs.get('mcp_strategy') == 'best-effort'

    # max_search_results should have been converted to int and set on cfg
    assert br.gpt_researcher.cfg.max_search_results_per_query == 7


def test_init_without_optionals_round_051(monkeypatch):
    # Patch GPTResearcher and the id generator again for determinism
    monkeypatch.setattr(br_mod, 'GPTResearcher', FakeGPTResearcher)
    monkeypatch.setattr(br_mod.BasicReport, '_generate_research_id', lambda self, q: 'fixed-id-2')

    custom_headers = {'Authorization': 'Bearer x'}
    br = br_mod.BasicReport(
        query='another',
        query_domains=[],
        report_type='typeB',
        report_source='sourceY',
        source_urls=[],
        document_urls=[],
        tone=None,
        config_path='',
        websocket=make_dummy_ws(),
        headers=custom_headers,  # ensure provided headers are preserved
        mcp_configs=None,
        mcp_strategy=None,
        max_search_results=None,
    )

    # Provided headers should be preserved rather than replaced by {}
    assert br.headers is custom_headers

    # research_id uses the second deterministic stub
    assert br.research_id == 'fixed-id-2'

    # gpt_researcher should exist, but its kwargs should not contain mcp keys
    assert isinstance(br.gpt_researcher, FakeGPTResearcher)
    assert 'mcp_configs' not in br.gpt_researcher.kwargs
    assert 'mcp_strategy' not in br.gpt_researcher.kwargs

    # max_search_results was None, so cfg.max_search_results_per_query should remain None
    assert br.gpt_researcher.cfg.max_search_results_per_query is None
