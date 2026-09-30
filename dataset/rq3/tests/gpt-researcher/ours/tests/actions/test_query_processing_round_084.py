import asyncio
import importlib
import types
import pytest

# Tests for plan_research_outline (round 84)
# Each test name ends with _round_084 as required.

@pytest.mark.asyncio
async def test_plan_research_outline_mcp_only_round_084(monkeypatch):
    """
    When retriever_names contains only 'mcp', the function should log and return the
    original query immediately without calling generate_sub_queries.
    """
    qp = importlib.import_module("gpt_researcher.actions.query_processing")

    # Prepare a fake generate_sub_queries that would fail if called
    async def _bad_generate(*args, **kwargs):
        raise AssertionError("generate_sub_queries should not be called for MCP-only")

    monkeypatch.setattr(qp, "generate_sub_queries", _bad_generate)

    # Capture logger.info calls
    calls = []

    class _Logger:
        def info(self, *a, **k):
            calls.append((a, k))

    monkeypatch.setattr(qp, "logger", _Logger())

    query = "original query"
    result = await qp.plan_research_outline(
        query=query,
        search_results=[],
        agent_role_prompt="role",
        cfg=types.SimpleNamespace(),
        parent_query="parent",
        report_type="report",
        cost_callback=None,
        retriever_names=["mcp"],
    )

    # Verify returned value is the original query wrapped in a list
    assert result == [query]
    # Check that logger.info was called at least once with a message mentioning MCP
    assert any("MCP" in (a[0] if a else "") or "mcp" in (a[0] if a else "") for (a, _) in calls)


@pytest.mark.asyncio
async def test_plan_research_outline_mcp_with_other_round_084(monkeypatch):
    """
    When retriever_names contains 'mcp' and other retrievers, the function should
    not return early and should call generate_sub_queries, returning its result.
    """
    qp = importlib.import_module("gpt_researcher.actions.query_processing")

    # Prepare a fake generate_sub_queries that returns a known list
    async def _fake_generate(query, parent_query, report_type, search_results, cfg, cost_callback, **kwargs):
        # Assert we receive forwarded args to ensure correct call shape
        assert query == "original"
        assert parent_query == "parent"
        assert report_type == "report"
        return ["subquery-1", "subquery-2"]

    monkeypatch.setattr(qp, "generate_sub_queries", _fake_generate)

    # Capture logger.info calls to ensure the MCP-with-others path logs something
    logged = []

    class _Logger:
        def info(self, *a, **k):
            logged.append(a)

    monkeypatch.setattr(qp, "logger", _Logger())

    result = await qp.plan_research_outline(
        query="original",
        search_results=[{"title": "r1"}],
        agent_role_prompt="role",
        cfg=types.SimpleNamespace(),
        parent_query="parent",
        report_type="report",
        cost_callback=None,
        retriever_names=["mcp", "other_retriever"],
    )

    # The fake generate_sub_queries return value should be propagated
    assert result == ["subquery-1", "subquery-2"]
    # Ensure we logged the MCP-with-others path
    assert any("MCP" in (a[0] if a else "") or "mcp" in (a[0] if a else "") or logged for logged in [logged])


@pytest.mark.asyncio
async def test_plan_research_outline_none_retriever_round_084(monkeypatch):
    """
    When retriever_names is None, it should be treated as an empty list and proceed
    to generate_sub_queries normally.
    """
    qp = importlib.import_module("gpt_researcher.actions.query_processing")

    # Fake generate_sub_queries to verify it's called and return a deterministic result
    called = {}

    async def _fake_generate2(query, parent_query, report_type, search_results, cfg, cost_callback, **kwargs):
        called['args'] = (query, parent_query, report_type)
        return ["generated-1"]

    monkeypatch.setattr(qp, "generate_sub_queries", _fake_generate2)

    result = await qp.plan_research_outline(
        query="Q",
        search_results=[],
        agent_role_prompt="role",
        cfg=types.SimpleNamespace(),
        parent_query="P",
        report_type="R",
        cost_callback=None,
        retriever_names=None,
    )

    assert result == ["generated-1"]
    # Ensure the fake was called with expected forwarded arguments
    assert called['args'] == ("Q", "P", "R")
