import asyncio
import pytest

import backend.report_type.deep_research.example as example


class MockResearcher:
    def __init__(
        self,
        query,
        report_type=None,
        report_source=None,
        tone=None,
        websocket=None,
        config_path=None,
        headers=None,
    ):
        # preserve shape of constructor and store values for assertions
        self.query = query
        self.report_type = report_type
        self.report_source = report_source
        self.tone = tone
        self.websocket = websocket
        self.config_path = config_path
        self.headers = headers

        # attributes that will be set by DeepResearch.run
        self.context = None
        self.visited_urls = None

    async def write_report(self):
        # deterministic return value
        return "REPORT: deterministic"


@pytest.mark.asyncio
async def test_run_with_citations_round_070(monkeypatch):
    # Patch GPTResearcher in the module under test
    monkeypatch.setattr(example, "GPTResearcher", MockResearcher)

    # Prepare to capture the query passed into deep_research
    captured = {}

    async def fake_generate_feedback(self, query, num_questions=None):
        # emulate follow up questions generation
        assert query == "initial-test-query"
        return ["What is X?"]

    async def fake_deep_research(self, query, breadth, depth, on_progress=None, **kwargs):
        # capture the combined_query that was built in run
        captured['query_sent_to_deep_research'] = query
        captured['breadth'] = breadth
        captured['depth'] = depth
        # assert on_progress was forwarded (could be None)
        captured['on_progress_passed'] = on_progress
        # return results with a citation to force the citation branch
        return {
            'learnings': ['Finding A'],
            'citations': {'Finding A': 'http://source.example'},
            'visited_urls': ['http://visited.example']
        }

    # Patch the async methods on DeepResearch
    monkeypatch.setattr(example.DeepResearch, "generate_feedback", fake_generate_feedback)
    monkeypatch.setattr(example.DeepResearch, "deep_research", fake_deep_research)

    # Instantiate DeepResearch with expected signature
    dr = example.DeepResearch(
        query="initial-test-query",
        breadth=2,
        depth=1,
        websocket=None,
        tone="neutral",
        config_path="/tmp/config",
        headers={"h": "v"},
        concurrency_limit=1,
    )

    # create a sentinel on_progress callable and call run
    async def progress_fn(step):
        # simple noop progress function
        return step

    report = await dr.run(on_progress=progress_fn)

    # Assertions
    assert report == "REPORT: deterministic"

    # The combined_query built in run should include the initial query and the Q/A
    sent_q = captured['query_sent_to_deep_research']
    assert "Initial Query: initial-test-query" in sent_q
    assert "Q: What is X?\nA: Automatically proceeding with research" in sent_q

    # researcher.context should have the citation appended in the expected format
    # We can access the MockResearcher instance via the fact that write_report returned its deterministic string
    # But we also know that the module assigns researcher.context before calling write_report
    # Create another run to inspect the researcher object directly by patching write_report to return it


@pytest.mark.asyncio
async def test_run_with_and_without_citations_round_070(monkeypatch):
    # This test ensures both branches in the loop are exercised: one learning with citation and one without
    monkeypatch.setattr(example, "GPTResearcher", MockResearcher)

    async def fake_generate_feedback(self, query, num_questions=None):
        return ["Q1"]

    captured = {}

    async def fake_deep_research_mixed(self, query, breadth, depth, on_progress=None, **kwargs):
        # Return two learnings, one with citation and one without
        captured['query'] = query
        return {
            'learnings': ['Alpha', 'Beta'],
            'citations': {'Alpha': 'src-A'},
            'visited_urls': ['u1', 'u2']
        }

    # We'll patch write_report to return the researcher attributes so we can assert on them
    class InspectResearcher(MockResearcher):
        async def write_report(self):
            # return a dict-like representation as string to keep deterministic
            return f"CTX:{self.context};VISITED:{sorted(list(self.visited_urls))}"

    monkeypatch.setattr(example, "GPTResearcher", InspectResearcher)
    monkeypatch.setattr(example.DeepResearch, "generate_feedback", fake_generate_feedback)
    monkeypatch.setattr(example.DeepResearch, "deep_research", fake_deep_research_mixed)

    dr = example.DeepResearch(
        query="q-mixed",
        breadth=1,
        depth=1,
        websocket=None,
        tone=None,
        config_path=None,
        headers=None,
        concurrency_limit=1,
    )

    result = await dr.run(on_progress=None)

    # The returned report string encodes context and visited urls from our InspectResearcher
    assert result.startswith("CTX:")
    # Extract context part
    ctx_part = result.split(";VISITED:")[0][4:]
    visited_part = result.split(";VISITED:")[1]

    # Context should contain both lines; Alpha should have source, Beta should not
    assert "Alpha [Source: src-A]" in ctx_part
    assert "Beta" in ctx_part

    # Visited urls should reflect the list from deep_research
    assert "u1" in visited_part and "u2" in visited_part
