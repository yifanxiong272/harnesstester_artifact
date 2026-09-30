# file: gpt_researcher/actions/query_processing.py:112-169
# asked: {"lines": [140, 141, 145, 146, 147, 149, 151, 153, 156, 159, 160, 161, 162, 163, 164, 165, 166, 169], "branches": [[140, 141], [140, 145], [145, 146], [145, 159], [149, 151], [149, 156]]}
# gained: {"lines": [140, 141, 145, 146, 147, 149, 151, 153, 156, 159, 160, 161, 162, 163, 164, 165, 166, 169], "branches": [[140, 141], [140, 145], [145, 146], [145, 159], [149, 151], [149, 156]]}

import asyncio
from types import SimpleNamespace
import pytest

import gpt_researcher.actions.query_processing as qp


async def _async_fail(*args, **kwargs):
    pytest.fail("generate_sub_queries should not be called for MCP-only retriever")


def test_mcp_only_skips_generation(monkeypatch):
    """If retriever_names contains only 'mcp', the function should return [query]
    and not call generate_sub_queries. Also should log the MCP-only message.
    """
    # ensure generate_sub_queries won't be called
    monkeypatch.setattr(qp, "generate_sub_queries", _async_fail, raising=False)

    # capture logger messages
    messages = []

    class DummyLogger:
        def info(self, msg):
            messages.append(msg)

    monkeypatch.setattr(qp, "logger", DummyLogger(), raising=False)

    query = "test query"
    res = asyncio.run(
        qp.plan_research_outline(
            query=query,
            search_results=[],
            agent_role_prompt="role",
            cfg=SimpleNamespace(),  # dummy cfg
            parent_query="parent",
            report_type="report",
            retriever_names=["mcp"],
        )
    )

    assert res == [query]
    # Ensure the exact MCP-only message was logged
    assert "Using MCP retriever only - skipping sub-query generation" in messages


def test_no_retriever_names_calls_generate_sub_queries(monkeypatch):
    """When retriever_names is None, it should be treated as [] and call generate_sub_queries.
    Ensure the arguments forwarded to generate_sub_queries match the expected order.
    """
    recorded = []

    async def stub(*args, **kwargs):
        recorded.append((args, kwargs))
        return ["sub1", "sub2"]

    monkeypatch.setattr(qp, "generate_sub_queries", stub, raising=False)

    # Provide a dummy logger to avoid side-effects
    monkeypatch.setattr(qp, "logger", SimpleNamespace(info=lambda *a, **k: None), raising=False)

    query = "main query"
    search_results = [{"title": "r1"}]
    agent_role_prompt = "role"
    cfg = SimpleNamespace(param=1)
    parent_query = "parentQ"
    report_type = "typeA"

    # Use a dummy cost callback to ensure it is forwarded
    def cost_cb(x):
        return 0.5

    result = asyncio.run(
        qp.plan_research_outline(
            query=query,
            search_results=search_results,
            agent_role_prompt=agent_role_prompt,
            cfg=cfg,
            parent_query=parent_query,
            report_type=report_type,
            cost_callback=cost_cb,
            retriever_names=None,  # explicit None to test branch
            extra_kw="extra",  # ensure kwargs forwarded
        )
    )

    assert result == ["sub1", "sub2"]
    # assert generate_sub_queries was called exactly once
    assert len(recorded) == 1
    call_args, call_kwargs = recorded[0]
    # positional args: query, parent_query, report_type, search_results, cfg, cost_callback
    assert call_args[0] == query
    assert call_args[1] == parent_query
    assert call_args[2] == report_type
    assert call_args[3] == search_results
    assert call_args[4] == cfg
    assert call_args[5] is cost_cb
    # kwargs should include our extra_kw
    assert call_kwargs.get("extra_kw") == "extra"


def test_mcp_with_other_retrievers_generates_for_non_mcp(monkeypatch):
    """If 'mcp' is present alongside other retrievers, generate_sub_queries should be called
    and the logger should note that MCP is used with others.
    """
    recorded = []

    async def stub(*args, **kwargs):
        recorded.append((args, kwargs))
        return ["gen1"]

    monkeypatch.setattr(qp, "generate_sub_queries", stub, raising=False)

    messages = []

    class DummyLogger:
        def info(self, msg):
            messages.append(msg)

    monkeypatch.setattr(qp, "logger", DummyLogger(), raising=False)

    result = asyncio.run(
        qp.plan_research_outline(
            query="Q",
            search_results=[],
            agent_role_prompt="role",
            cfg=SimpleNamespace(),
            parent_query="P",
            report_type="R",
            retriever_names=["mcp", "web"],
        )
    )

    assert result == ["gen1"]
    # ensure generate_sub_queries was called
    assert len(recorded) == 1
    # ensure logger noted MCP with others using the exact message
    assert "Using MCP with other retrievers - generating sub-queries for non-MCP retrievers" in messages
