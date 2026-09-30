# file: gpt_researcher/actions/query_processing.py:112-169
# asked: {"lines": [140, 141, 145, 146, 147, 149, 151, 153, 156, 159, 160, 161, 162, 163, 164, 165, 166, 169], "branches": [[140, 141], [140, 145], [145, 146], [145, 159], [149, 151], [149, 156]]}
# gained: {"lines": [140, 141, 145, 146, 147, 149, 151, 153, 156, 159, 160, 161, 162, 163, 164, 165, 166, 169], "branches": [[140, 141], [140, 145], [145, 146], [145, 159], [149, 151], [149, 156]]}

import importlib
import asyncio
import pytest
from types import SimpleNamespace

MODULE_CANDIDATES = [
    "gpt_researcher.actions.query_processing",
    "gpt_researcher.gpt_researcher.actions.query_processing",
    "gpt_researcher.actions.query_processing.plan_research_outline",  # unlikely, but harmless
]

def _import_module():
    for name in MODULE_CANDIDATES:
        try:
            mod = importlib.import_module(name)
            # ensure it has the function we need
            if hasattr(mod, "plan_research_outline"):
                return mod
        except Exception:
            continue
    raise ImportError("Could not import query_processing module from known candidates.")

@pytest.mark.asyncio
async def test_retriever_names_none_calls_generate_sub_queries(monkeypatch):
    mod = _import_module()
    called = {}

    async def fake_generate_sub_queries(query, parent_query, report_type, search_results, cfg, cost_callback, **kwargs):
        # record that we were called and the values we received
        called['args'] = {
            "query": query,
            "parent_query": parent_query,
            "report_type": report_type,
            "search_results": search_results,
            "cfg": cfg,
            "cost_callback": cost_callback,
            "kwargs": kwargs,
        }
        return ["subquery-from-fake"]

    # Patch the generate_sub_queries in the module
    monkeypatch.setattr(mod, "generate_sub_queries", fake_generate_sub_queries)

    query = "What is the capital of France?"
    search_results = [{"title": "Paris - Wikipedia"}]
    agent_role_prompt = "role"
    cfg = SimpleNamespace()  # minimal stand-in for Config
    parent_query = "parent"
    report_type = "report"

    # retriever_names = None should be handled and set to []
    result = await mod.plan_research_outline(
        query=query,
        search_results=search_results,
        agent_role_prompt=agent_role_prompt,
        cfg=cfg,
        parent_query=parent_query,
        report_type=report_type,
        cost_callback=None,
        retriever_names=None,
    )

    assert result == ["subquery-from-fake"]
    assert "args" in called
    assert called["args"]["query"] == query
    assert called["args"]["parent_query"] == parent_query
    assert called["args"]["report_type"] == report_type
    assert called["args"]["search_results"] == search_results
    assert called["args"]["cfg"] is cfg
    # Ensure kwargs exists and is a dict
    assert isinstance(called["args"]["kwargs"], dict)

@pytest.mark.asyncio
async def test_mcp_only_skips_generation_lowercase(monkeypatch):
    mod = _import_module()

    async def fail_generate(*args, **kwargs):
        raise AssertionError("generate_sub_queries should not be called for MCP-only retriever")

    monkeypatch.setattr(mod, "generate_sub_queries", fail_generate)

    query = "Find X"
    search_results = []
    agent_role_prompt = "role"
    cfg = SimpleNamespace()
    parent_query = ""
    report_type = "summary"

    result = await mod.plan_research_outline(
        query=query,
        search_results=search_results,
        agent_role_prompt=agent_role_prompt,
        cfg=cfg,
        parent_query=parent_query,
        report_type=report_type,
        cost_callback=None,
        retriever_names=["mcp"],
    )

    assert result == [query]

@pytest.mark.asyncio
async def test_mcp_only_skips_generation_uppercase(monkeypatch):
    mod = _import_module()

    async def fail_generate(*args, **kwargs):
        raise AssertionError("generate_sub_queries should not be called for MCP-only retriever (MCPRetriever)")

    monkeypatch.setattr(mod, "generate_sub_queries", fail_generate)

    query = "Find Y"
    search_results = []
    agent_role_prompt = "role"
    cfg = SimpleNamespace()
    parent_query = ""
    report_type = "detailed"

    result = await mod.plan_research_outline(
        query=query,
        search_results=search_results,
        agent_role_prompt=agent_role_prompt,
        cfg=cfg,
        parent_query=parent_query,
        report_type=report_type,
        cost_callback=None,
        retriever_names=["MCPRetriever"],
    )

    assert result == [query]

@pytest.mark.asyncio
async def test_mcp_with_other_retrievers_calls_generate(monkeypatch):
    mod = _import_module()
    called = {}

    async def fake_generate_sub_queries(query, parent_query, report_type, search_results, cfg, cost_callback, **kwargs):
        called['was_called'] = True
        called['query'] = query
        return ["from-mcp-and-others"]

    monkeypatch.setattr(mod, "generate_sub_queries", fake_generate_sub_queries)

    query = "Investigate Z"
    search_results = [{"title": "Doc"}]
    agent_role_prompt = "role"
    cfg = SimpleNamespace()
    parent_query = "root"
    report_type = "brief"

    result = await mod.plan_research_outline(
        query=query,
        search_results=search_results,
        agent_role_prompt=agent_role_prompt,
        cfg=cfg,
        parent_query=parent_query,
        report_type=report_type,
        cost_callback=None,
        retriever_names=["mcp", "vector"],
    )

    assert called.get('was_called', False) is True
    assert called['query'] == query
    assert result == ["from-mcp-and-others"]
