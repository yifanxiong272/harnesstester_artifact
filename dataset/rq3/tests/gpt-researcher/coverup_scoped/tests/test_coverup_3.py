# file: gpt_researcher/skills/deep_research.py:372-534
# asked: {"lines": [383, 384, 385, 386, 387, 388, 389, 391, 393, 394, 397, 398, 399, 400, 402, 403, 404, 405, 406, 409, 411, 412, 413, 414, 415, 416, 418, 419, 420, 423, 424, 425, 426, 427, 429, 430, 434, 437, 438, 441, 442, 443, 447, 448, 449, 450, 452, 453, 454, 455, 456, 457, 458, 459, 462, 463, 464, 465, 466, 467, 470, 471, 472, 475, 476, 477, 480, 481, 482, 483, 484, 485, 486, 487, 490, 491, 492, 493, 496, 497, 498, 502, 503, 504, 505, 506, 507, 508, 509, 512, 513, 514, 515, 516, 517, 518, 521, 522, 525, 526, 528, 529, 530, 531, 532, 533], "branches": [[384, 385], [384, 386], [386, 387], [386, 388], [388, 389], [388, 391], [393, 394], [393, 397], [415, 416], [415, 418], [449, 450], [449, 452], [476, 477], [476, 480], [480, 481], [480, 521], [484, 485], [484, 486], [486, 487], [486, 490], [490, 480], [490, 491], [515, 516], [515, 517], [517, 480], [517, 518]]}
# gained: {"lines": [383, 384, 385, 386, 387, 388, 389, 391, 393, 394, 397, 398, 399, 400, 402, 403, 404, 405, 406, 409, 411, 412, 413, 414, 415, 416, 418, 419, 420, 423, 424, 425, 426, 427, 429, 430, 434, 437, 438, 441, 442, 443, 447, 448, 449, 450, 452, 453, 454, 455, 456, 457, 458, 459, 462, 463, 464, 465, 466, 467, 470, 471, 472, 475, 476, 477, 480, 481, 482, 483, 484, 485, 486, 487, 490, 491, 492, 493, 496, 497, 498, 502, 503, 504, 505, 506, 507, 508, 509, 512, 513, 514, 515, 516, 517, 518, 521, 522, 525, 526, 528, 529, 530, 531, 532, 533], "branches": [[384, 385], [384, 386], [386, 387], [386, 388], [388, 389], [388, 391], [393, 394], [393, 397], [415, 416], [415, 418], [449, 450], [476, 477], [476, 480], [480, 481], [480, 521], [484, 485], [486, 487], [490, 480], [490, 491], [515, 516], [517, 518]]}

import asyncio
import importlib
import types
import sys
import pytest

# Import the module and class under test
dr_mod = importlib.import_module("gpt_researcher.skills.deep_research")
DeepResearchSkill = dr_mod.DeepResearchSkill

# Helper fake parent researcher to initialize DeepResearchSkill
class FakeParentCfg:
    def __init__(self):
        self.deep_research_breadth = 2
        self.deep_research_depth = 2
        self.deep_research_concurrency = 2
        self.config_path = "/fake/config"

class FakeParentResearcher:
    def __init__(self):
        self.cfg = FakeParentCfg()
        self.websocket = None
        self.tone = "neutral"
        self.headers = {"h": "v"}
        self.visited_urls = set()
        self.mcp_configs = {"mcp": True}
        self.mcp_strategy = "strategy"

# Fake GPTResearcher used by deep_research when it imports GPTResearcher from parent package
class FakeGPTResearcher:
    def __init__(self, **kwargs):
        # expose what deep_research expects: visited_urls and research_sources
        self._raise = kwargs.get("raise_on_conduct", False)
        self.visited_urls = kwargs.get("visited_urls", set())
        self.research_sources = kwargs.get("research_sources", [])
        self.query = kwargs.get("query", "")
    async def conduct_research(self):
        if self._raise:
            raise RuntimeError("simulated conduct_research error")
        return [f"context for {self.query}"]

@pytest.mark.asyncio
async def test_deep_research_success_recursive(monkeypatch):
    """
    Test the normal successful path of deep_research including a recursive deeper call (depth>1).
    Verifies that learnings, citations, visited_urls, context, sources are aggregated and that
    the instance fields context and research_sources are extended.
    """
    parent = FakeParentResearcher()
    skill = DeepResearchSkill(parent)

    # Create a fake package module 'gpt_researcher' and insert into sys.modules so that
    # "from .. import GPTResearcher" inside deep_research resolves to this module.
    pkg = types.ModuleType("gpt_researcher")
    # Put a default GPTResearcher that we'll overwrite later per-test
    pkg.GPTResearcher = FakeGPTResearcher
    monkeypatch.setitem(sys.modules, "gpt_researcher", pkg)

    # 2) Replace trim_context_to_word_limit to return the context list unchanged
    monkeypatch.setattr(dr_mod, "trim_context_to_word_limit", lambda ac: ac, raising=False)

    # 3) Replace logger to a no-op object to avoid side-effects
    class DummyLogger:
        def info(self, *a, **k): pass
        def error(self, *a, **k): pass
    monkeypatch.setattr(dr_mod, "logger", DummyLogger(), raising=False)

    # Setup generate_search_queries to produce different queries depending on whether
    # it's a recursive call or the initial call. Use presence of 'Previous research goal' to detect recursion.
    async def fake_generate_search_queries(query: str, num_queries: int = 3):
        if "Previous research goal" in (query or ""):
            return [{"query": "sub-query", "researchGoal": "subgoal"}]
        return [{"query": "main-query", "researchGoal": "maingoal"}]
    monkeypatch.setattr(skill, "generate_search_queries", fake_generate_search_queries, raising=False)

    # Setup process_research_results to return distinct outputs for main and sub queries
    async def fake_process_research_results(query: str, context: str, num_learnings: int = 3):
        if "sub-query" in (query or "") or "Follow-up questions" in (query or ""):
            return {
                "learnings": ["L2"],
                "followUpQuestions": [],
                "citations": {"c2": "url2"}
            }
        return {
            "learnings": ["L1"],
            "followUpQuestions": ["fq1"],
            "citations": {"c1": "url1"}
        }
    monkeypatch.setattr(skill, "process_research_results", fake_process_research_results, raising=False)

    # Replace GPTResearcher in our fake package with a factory to return different visited/sources by query
    def GPTResearcher_factory(**kwargs):
        q = kwargs.get("query", "")
        if "main-query" in q:
            return FakeGPTResearcher(query=q, visited_urls={"v_main"}, research_sources=["s_main"])
        return FakeGPTResearcher(query=q, visited_urls={"v_sub"}, research_sources=["s_sub"])
    setattr(pkg, "GPTResearcher", GPTResearcher_factory)

    # Use an on_progress collector to ensure it's invoked and mutated progress object is plausible
    progress_updates = []
    def on_progress(p):
        progress_updates.append((getattr(p, "current_query", None), getattr(p, "current_breadth", None),
                                 getattr(p, "completed_queries", None), getattr(p, "current_depth", None)))
    # Run deep_research with depth=2 to trigger recursion
    result = await skill.deep_research(query="Initial query", breadth=2, depth=2, on_progress=on_progress)

    # Assertions on returned aggregated result
    assert set(result["learnings"]) == {"L1", "L2"}
    # visited urls should include both main and sub visited sets
    assert set(result["visited_urls"]) >= {"v_main", "v_sub"}
    # citations merged
    assert result["citations"].get("c1") == "url1"
    assert result["citations"].get("c2") == "url2"
    # context should contain contexts from both levels (trim function returned unchanged)
    assert any("main-query" in (c if isinstance(c, str) else "") for c in result["context"])
    assert any("sub-query" in (c if isinstance(c, str) else "") for c in result["context"])
    # sources aggregated
    assert "s_main" in result["sources"] and "s_sub" in result["sources"]
    # ensure instance fields were extended
    assert any("main-query" in (c if isinstance(c, str) else "") for c in skill.context)
    assert ("s_main" in skill.research_sources) or ("s_sub" in skill.research_sources)
    # ensure on_progress was invoked at least once and shows changing completed_queries or depths
    assert len(progress_updates) >= 1
    # ensure returned learnings deduplicated by set() in result (should be length 2)
    assert len(result["learnings"]) == 2

@pytest.mark.asyncio
async def test_deep_research_handles_exceptions(monkeypatch):
    """
    Test that when the nested researcher raises an exception during conduct_research,
    the exception is caught, the query result is ignored, and the function returns without crashing.
    """
    parent = FakeParentResearcher()
    skill = DeepResearchSkill(parent)

    # Create fake package module and insert into sys.modules
    pkg = types.ModuleType("gpt_researcher")
    monkeypatch.setitem(sys.modules, "gpt_researcher", pkg)

    # Patch GPTResearcher to a version that raises on conduct_research
    def GPTResearcher_error_factory(**kwargs):
        return FakeGPTResearcher(query=kwargs.get("query", ""), raise_on_conduct=True)
    setattr(pkg, "GPTResearcher", GPTResearcher_error_factory)

    # Ensure generate_search_queries returns a single query
    async def fake_generate_search_queries(query: str, num_queries: int = 3):
        return [{"query": "will-error", "researchGoal": "goal-error"}]
    monkeypatch.setattr(skill, "generate_search_queries", fake_generate_search_queries, raising=False)

    # process_research_results should not be called (since conduct_research raises), but provide a dummy to be safe
    async def fake_process_research_results(query: str, context: str, num_learnings: int = 3):
        return {"learnings": ["X"], "followUpQuestions": [], "citations": {}}
    monkeypatch.setattr(skill, "process_research_results", fake_process_research_results, raising=False)

    # Monkeypatch trim and logger to simple versions
    monkeypatch.setattr(dr_mod, "trim_context_to_word_limit", lambda ac: ac, raising=False)

    class CaptureLogger:
        def __init__(self):
            self.errors = []
        def info(self, *a, **k): pass
        def error(self, *a, **k):
            self.errors.append((a, k))
    cap_logger = CaptureLogger()
    monkeypatch.setattr(dr_mod, "logger", cap_logger, raising=False)

    # Run deep_research; it should complete without raising despite the inner error
    result = await skill.deep_research(query="Trigger error", breadth=1, depth=1)

    # Since the only query errored out, results should be empty/initial values (no learnings, no visited urls)
    assert result["learnings"] == []
    assert result["visited_urls"] == []
    assert result["citations"] == {}
    # context should be whatever trim returned (empty)
    assert result["context"] == []
    # ensure logger.error was called at least once
    assert len(cap_logger.errors) >= 1
