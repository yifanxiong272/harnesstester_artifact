import asyncio
from types import SimpleNamespace
import pytest

from gpt_researcher import __name__ as _pkg_name  # ensure package import
from gpt_researcher.skills import deep_research as dr

# Provide pytest-asyncio marker if available; fallback to asyncio loop
pytestmark = pytest.mark.asyncio


class FakeGPTResearcher:
    def __init__(self, *args, **kwargs):
        # accept all constructor args used by deep_research
        self._constructed_with = kwargs
        # default attributes that deep_research reads after conduct_research
        self.visited_urls = set()
        self.research_sources = []

    async def conduct_research(self):
        # default behavior, can be monkeypatched by instance
        return ["default_context"]


async def _call_deep_research_with_dummy(dummy, **kwargs):
    # Helper to call the unbound method as the class method would
    return await dr.DeepResearchSkill.deep_research(dummy, **kwargs)


@pytest.fixture(autouse=True)
def patch_package_gptresearcher(monkeypatch):
    """Patch the parent package to expose FakeGPTResearcher for the relative import
    that occurs inside deep_research (from .. import GPTResearcher).
    Also patch trim_context_to_word_limit to a predictable identity function.
    """
    import gpt_researcher

    # Patch GPTResearcher on the package so `from .. import GPTResearcher` finds it
    monkeypatch.setattr(gpt_researcher, "GPTResearcher", FakeGPTResearcher, raising=False)

    # Patch trim_context_to_word_limit to deterministic identity-like behavior
    monkeypatch.setattr(dr, "trim_context_to_word_limit", lambda ctx: list(ctx), raising=True)

    yield


@pytest.mark.asyncio
async def test_deep_research_success_round_003():
    # Arrange: prepare a dummy "self" object with the attributes and async methods
    calls = []

    class DummySelf:
        def __init__(self):
            self.concurrency_limit = 1
            self.tone = "neutral"
            self.websocket = None
            self.config_path = None
            self.headers = {}
            self.visited_urls = set()
            # researcher must provide mcp_configs and mcp_strategy
            self.researcher = SimpleNamespace(mcp_configs={"k": "v"}, mcp_strategy="strat")
            self.context = []
            self.research_sources = []

        async def generate_search_queries(self, query, num_queries):
            # Return a single SERP-like query dict to exercise the main path
            return [{
                "query": "search-term",
                "researchGoal": "Understand X"
            }]

        async def process_research_results(self, query, context):
            # Simulate extracting learnings and follow-ups
            return {
                "learnings": ["Finding A"],
                "followUpQuestions": ["What about B?"],
                "citations": {"cite1": "http://example.com"}
            }

    dummy = DummySelf()

    # Patch the FakeGPTResearcher instance behavior created inside deep_research
    # by intercepting its conduct_research to return a list context and set visited/sources
    original_fake_init = FakeGPTResearcher.__init__

    def fake_init(self, *args, **kwargs):
        original_fake_init(self, *args, **kwargs)

        async def conduct_research_override():
            # return a list to exercise the context join/append branch
            return ["ctx-item-1"]

        self.conduct_research = conduct_research_override
        self.visited_urls = {"http://site1"}
        self.research_sources = ["source1"]

    FakeGPTResearcher.__init__ = fake_init

    progress_states = []

    def on_progress(p):
        # capture a subset of progress attributes deterministically
        progress_states.append((p.total_depth, p.total_breadth, p.total_queries, p.current_breadth))

    # Act
    result = await _call_deep_research_with_dummy(dummy, query="top-query", breadth=1, depth=1, learnings=None, citations=None, visited_urls=None, on_progress=on_progress)

    # Restore patched init to avoid cross-test pollution
    FakeGPTResearcher.__init__ = original_fake_init

    # Assert: returned structure aggregates the fake research results
    assert isinstance(result, dict)
    assert "Finding A" in result["learnings"]
    assert "http://site1" in result["visited_urls"]
    assert result["citations"].get("cite1") == "http://example.com"
    # Context should include the string joined from the returned context list
    assert any("ctx-item-1" in c for c in result["context"])
    # Sources propagated
    assert "source1" in result["sources"]

    # Internal state on dummy should have been extended
    assert any("ctx-item-1" in c for c in dummy.context)
    assert "source1" in dummy.research_sources

    # on_progress must have been called at least once and reflect total_queries being set
    assert any(ts[2] >= 0 for ts in progress_states)


@pytest.mark.asyncio
async def test_deep_research_handles_exception_round_003():
    # Arrange: generate_search_queries returns one query, but the researcher raises
    class DummySelfErr:
        def __init__(self):
            self.concurrency_limit = 1
            self.tone = "neutral"
            self.websocket = None
            self.config_path = None
            self.headers = {}
            self.visited_urls = set()
            self.researcher = SimpleNamespace(mcp_configs={}, mcp_strategy=None)
            self.context = []
            self.research_sources = []

        async def generate_search_queries(self, query, num_queries):
            return [{"query": "bad-search", "researchGoal": "X"}]

        async def process_research_results(self, query, context):
            # Should not be reached in this test because conduct_research will raise
            return {"learnings": [], "followUpQuestions": [], "citations": {}}

    dummy = DummySelfErr()

    # Make FakeGPTResearcher.conduct_research raise to hit exception branch inside process_query
    original_fake_init = FakeGPTResearcher.__init__

    def fake_init_raise(self, *args, **kwargs):
        original_fake_init(self, *args, **kwargs)

        async def conduct_research_raise():
            raise RuntimeError("boom")

        self.conduct_research = conduct_research_raise
        self.visited_urls = set()
        self.research_sources = []

    FakeGPTResearcher.__init__ = fake_init_raise

    # Act: call deep_research and ensure it completes without raising
    result = await _call_deep_research_with_dummy(dummy, query="q", breadth=1, depth=1, learnings=None, citations=None, visited_urls=None, on_progress=None)

    # Restore patched init
    FakeGPTResearcher.__init__ = original_fake_init

    # Assert: when inner researcher raises, result should be empty aggregates (no exception escapes)
    assert result["learnings"] == []
    assert result["visited_urls"] == []
    assert result["citations"] == {}
    assert result["context"] == []
    assert result["sources"] == []
