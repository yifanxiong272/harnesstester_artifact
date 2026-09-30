import asyncio
import pytest
import importlib

# Import the module under test
example = importlib.import_module("backend.report_type.deep_research.example")

# Create predictable fake GPTResearcher used to replace the real one inside the module
class FakeGPTResearcher:
    def __init__(self, *args, query=None, **kwargs):
        # store the query so behavior can depend on it
        self.query = query if query is not None else kwargs.get('query')
        self.context = {"ctx": f"context_for_{self.query}"}
        self.visited_urls = [f"url_for_{self.query}"]

    async def conduct_research(self):
        # deterministically fail for queries containing the token 'bad' to exercise the exception path
        if self.query and 'bad' in self.query:
            raise RuntimeError("simulated conduct_research failure")
        # no-op otherwise
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_deep_research_handles_exceptions_round_011(monkeypatch):
    """Verify deep_research filters out failed queries and updates on_progress"""
    # Patch the GPTResearcher used inside the module so no external calls occur
    monkeypatch.setattr(example, "GPTResearcher", FakeGPTResearcher)

    # Prepare a fake self with required attributes and async helper methods
    class FakeSelf:
        def __init__(self):
            self.concurrency_limit = 2
            self.tone = "neutral"
            self.websocket = None
            self.config_path = None
            self.headers = {}

        async def generate_serp_queries(self, query, num_queries):
            # Return two queries: one good, one that will cause FakeGPTResearcher.conduct_research to raise
            return [
                {"query": "good_query", "researchGoal": "goal_good"},
                {"query": "bad_query", "researchGoal": "goal_bad"},
            ]

        async def process_serp_result(self, query, context, num_learnings=None):
            # If query relates to good_query, return deterministic results
            if "good_query" in query:
                return {
                    "learnings": [f"learning_{query}"],
                    "followUpQuestions": ["q1", "q2"],
                    "researchGoal": f"goal_for_{query}",
                    "citations": {f"cite_{query}": "source"},
                }
            # Should not be reached for bad_query because conduct_research will raise, but keep safe fallback
            return {
                "learnings": [],
                "followUpQuestions": [],
                "researchGoal": "",
                "citations": {},
            }

    fself = FakeSelf()

    # Collect progress snapshots to assert on_progress was invoked
    progress_snapshots = []

    def on_progress(progress):
        # store a tuple snapshot of interesting fields
        progress_snapshots.append((progress.current_query, progress.completed_queries, progress.total_queries))

    # Call the original deep_research implementation bound to our fake instance
    original = example.DeepResearch.deep_research
    result = await original.__get__(fself)(
        query="start",
        breadth=2,
        depth=1,  # depth=1 to avoid recursion in this test
        learnings=None,
        citations=None,
        visited_urls=None,
        on_progress=on_progress,
    )

    # The bad_query should be filtered out; only good_query contributes
    assert any("learning_good_query" in item for item in result["learnings"]) or any("learning_good_query" in item for item in result.get("learnings", []))

    # visited_urls must contain the one from the good query
    assert any("url_for_good_query" in u for u in result["visited_urls"])

    # citations should include the citation from the successful query
    assert any(k.startswith("cite_") for k in result["citations"].keys())

    # on_progress must have been called at least for initial and update positions
    assert len(progress_snapshots) >= 2
    # At least one snapshot should show completed_queries incremented to 1
    assert any(snapshot[1] >= 1 for snapshot in progress_snapshots)


@pytest.mark.asyncio
async def test_deep_research_with_recursion_round_011(monkeypatch):
    """Verify deep_research calls recursive deep_research when depth>1 and collects deeper results"""
    # Patch the GPTResearcher used inside the module to avoid external effects
    monkeypatch.setattr(example, "GPTResearcher", FakeGPTResearcher)

    class FakeSelf:
        def __init__(self):
            self.concurrency_limit = 2
            self.tone = "neutral"
            self.websocket = None
            self.config_path = None
            self.headers = {}

        async def generate_serp_queries(self, query, num_queries):
            # Single query to keep the scenario simple
            return [{"query": "initial_query", "researchGoal": "initial_goal"}]

        async def process_serp_result(self, query, context, num_learnings=None):
            # deterministic result for the initial query
            return {
                "learnings": ["a1", "a2"],
                "followUpQuestions": ["follow1"],
                "researchGoal": "next_goal",
                "citations": {"c1": "s1"},
            }

    fself = FakeSelf()

    # Prepare the deeper_results that the recursive call should return
    deeper_results = {
        "learnings": ["deep_a", "deep_b"],
        "visited_urls": ["deep_url1"],
        "citations": {"deep_c": "deep_s"},
    }

    # Replace the instance's deep_research (used for recursion) with a coroutine returning deeper_results
    async def fake_recursive_deep_research(*args, **kwargs):
        return deeper_results

    fself.deep_research = fake_recursive_deep_research

    # Call the original deep_research bound to our fake instance with depth>1 to trigger recursion
    original = example.DeepResearch.deep_research
    result = await original.__get__(fself)(
        query="start",
        breadth=4,
        depth=2,  # triggers recursion branch
        learnings=None,
        citations=None,
        visited_urls=None,
        on_progress=None,
    )

    # According to implementation, after recursion, all_learnings is replaced by deeper_results['learnings']
    assert set(result["learnings"]) == set(deeper_results["learnings"])

    # visited_urls should match the deeper_results visited urls
    assert set(result["visited_urls"]) == set(deeper_results["visited_urls"]) 

    # citations should include deeper_results citations
    for k, v in deeper_results["citations"].items():
        assert result["citations"].get(k) == v
