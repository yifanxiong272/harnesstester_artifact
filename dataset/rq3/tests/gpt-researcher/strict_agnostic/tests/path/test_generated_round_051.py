import importlib
from types import SimpleNamespace
import pytest

# Import the module under test
mod = importlib.import_module("backend.report_type.basic_report.basic_report")
BasicReport = mod.BasicReport

class DummyGPTResearcher:
    """A deterministic stand-in for the real GPTResearcher used only in tests.
    It captures the kwargs it was constructed with and exposes a mutable cfg
    object so the BasicReport init can mutate cfg.max_search_results_per_query.
    """
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        # Start with a known value so tests can assert whether it was changed
        self.cfg = SimpleNamespace(max_search_results_per_query=1)


def _patch_gpt_and_id(monkeypatch, researcher_cls=None, fixed_id="fixed-research-id"):
    """Helper to patch GPTResearcher in the module and make research id deterministic."""
    # Ensure BasicReport._generate_research_id returns a deterministic id
    monkeypatch.setattr(BasicReport, "_generate_research_id", lambda self, q: fixed_id)
    # Replace GPTResearcher symbol in the module with provided researcher_cls
    if researcher_cls is None:
        researcher_cls = DummyGPTResearcher
    monkeypatch.setattr(mod, "GPTResearcher", researcher_cls)
    return fixed_id


def make_basic_report_instance(**kwargs):
    # Provide sensible defaults for required parameters so tests can override only needed ones
    params = {
        "query": "search terms",
        "query_domains": ["example.com"],
        "report_type": "type",
        "report_source": "source",
        "source_urls": ["http://u"],
        "document_urls": ["http://doc"],
        "tone": "neutral",
        "config_path": "/tmp/config",
        "websocket": object(),
    }
    params.update(kwargs)
    return BasicReport(**params)


def test_init_with_all_options_round_051(monkeypatch):
    """Construct BasicReport with mcp_configs, mcp_strategy and max_search_results.

    Assertions (oracle):
    - research_id is the patched deterministic value
    - headers default to an empty dict when None is provided
    - GPTResearcher was constructed and received mcp_configs and mcp_strategy in kwargs
    - max_search_results overrides the gpt_researcher.cfg.max_search_results_per_query
    """
    # Patch GPTResearcher and the research id generator
    _patch_gpt_and_id(monkeypatch, researcher_cls=DummyGPTResearcher, fixed_id="RID-ALL")

    # Provide optional values that should trigger the branches in __init__
    inst = make_basic_report_instance(
        headers=None,
        mcp_configs={"k": "v"},
        mcp_strategy="my-strategy",
        max_search_results="5",
    )

    # Basic attribute assignments
    assert inst.query == "search terms"
    # headers passed as None should become an empty dict (line 35)
    assert isinstance(inst.headers, dict) and inst.headers == {}

    # research_id should come from our patched generator (line 38)
    assert inst.research_id == "RID-ALL"

    # The gpt_researcher attribute should be an instance of our DummyGPTResearcher
    assert isinstance(inst.gpt_researcher, DummyGPTResearcher)

    # The GPTResearcher should have received the optional mcp params (lines 55-58)
    kw = inst.gpt_researcher.kwargs
    assert "mcp_configs" in kw and kw["mcp_configs"] == {"k": "v"}
    assert "mcp_strategy" in kw and kw["mcp_strategy"] == "my-strategy"

    # max_search_results should have been converted to int and applied to cfg (lines 63-64)
    assert inst.gpt_researcher.cfg.max_search_results_per_query == 5


def test_init_without_optionals_round_051(monkeypatch):
    """Construct BasicReport without optional MCP params and without max_search_results.

    Assertions (oracle):
    - provided headers are preserved
    - GPTResearcher was constructed but mcp keys are not present in its kwargs
    - cfg.max_search_results_per_query remains unchanged when max_search_results is None
    """
    # Create a custom Dummy that starts with a distinct cfg value to observe no change
    class DummyKeepCfg(DummyGPTResearcher):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            # Use a non-default sentinel to detect any modification
            self.cfg = SimpleNamespace(max_search_results_per_query=77)

    _patch_gpt_and_id(monkeypatch, researcher_cls=DummyKeepCfg, fixed_id="RID-NONE")

    provided_headers = {"auth": "token"}
    inst = make_basic_report_instance(
        headers=provided_headers,
        mcp_configs=None,
        mcp_strategy=None,
        max_search_results=None,
    )

    # Provided headers should be preserved (line 35)
    assert inst.headers is provided_headers

    # research_id patch
    assert inst.research_id == "RID-NONE"

    # Ensure GPTResearcher was constructed and that optional keys were omitted (lines 55-58)
    kw = inst.gpt_researcher.kwargs
    assert "mcp_configs" not in kw
    assert "mcp_strategy" not in kw

    # Since max_search_results was None, cfg should be unchanged (lines 63-64)
    assert inst.gpt_researcher.cfg.max_search_results_per_query == 77
