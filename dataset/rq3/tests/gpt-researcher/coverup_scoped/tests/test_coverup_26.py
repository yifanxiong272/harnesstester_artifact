# file: gpt_researcher/actions/query_processing.py:37-110
# asked: {"lines": [63, 64, 65, 66, 67, 68, 71, 72, 73, 74, 75, 76, 77, 79, 80, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 110], "branches": []}
# gained: {"lines": [63, 64, 65, 66, 67, 68, 71, 72, 73, 74, 75, 76, 77, 79, 80, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 110], "branches": []}

import json
from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_generate_sub_queries_success_first_attempt(monkeypatch):
    import importlib

    qp_mod = importlib.import_module("gpt_researcher.actions.query_processing")

    class DummyPromptFamily:
        @staticmethod
        def generate_search_queries_prompt(query, parent_query, report_type, max_iterations, context):
            return f"PROMPT for {query}|{parent_query}|{report_type}|{max_iterations}|{context}"

    cfg = SimpleNamespace(
        max_iterations=None,
        strategic_llm_model="strategic-model",
        strategic_llm_provider="strat-prov",
        llm_kwargs={"k": 1},
        strategic_token_limit=42,
        smart_llm_model="smart-model",
        smart_token_limit=99,
        smart_llm_provider="smart-prov",
        temperature=0.5,
    )

    captured = {}

    async def fake_create_chat_completion(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return json.dumps(["one", "two"])

    # Patch functions/attributes used by the module
    monkeypatch.setattr(qp_mod, "create_chat_completion", fake_create_chat_completion)
    # Ensure json_repair.loads uses the standard json.loads for parsing in tests
    monkeypatch.setattr(qp_mod.json_repair, "loads", json.loads)

    res = await qp_mod.generate_sub_queries(
        query="Q",
        parent_query="P",
        report_type="R",
        context=[{"a": 1}],
        cfg=cfg,
        cost_callback=None,
        prompt_family=DummyPromptFamily,
    )

    assert res == ["one", "two"]

    assert "kwargs" in captured
    assert captured["kwargs"].get("model") == cfg.strategic_llm_model
    msgs = captured["kwargs"].get("messages")
    assert isinstance(msgs, list)
    assert msgs[0]["role"] == "user"
    # Be permissive about exact formatting of context; just ensure prompt pieces are present
    assert "PROMPT for Q" in msgs[0]["content"]
    assert "|P|" in msgs[0]["content"] or "P|" in msgs[0]["content"]
    # The first attempt should include reasoning_effort
    assert "reasoning_effort" in captured["kwargs"]
    # Verify correctness of the ReasoningEfforts value if available
    if hasattr(qp_mod, "ReasoningEfforts"):
        assert captured["kwargs"]["reasoning_effort"] == qp_mod.ReasoningEfforts.Medium.value


@pytest.mark.asyncio
async def test_generate_sub_queries_retry_then_success(monkeypatch):
    import importlib

    qp_mod = importlib.import_module("gpt_researcher.actions.query_processing")

    class DummyPromptFamily:
        @staticmethod
        def generate_search_queries_prompt(query, parent_query, report_type, max_iterations, context):
            return "RETRY_PROMPT"

    cfg = SimpleNamespace(
        max_iterations=5,
        strategic_llm_model="strategic-model",
        strategic_llm_provider="strat-prov",
        llm_kwargs={},
        strategic_token_limit=1234,
        smart_llm_model="smart-model",
        smart_token_limit=888,
        smart_llm_provider="smart-prov",
        temperature=0.9,
    )

    calls = {"count": 0, "history": []}

    async def flaky_create_chat_completion(*args, **kwargs):
        calls["count"] += 1
        # store a copy so later modifications don't affect history
        calls["history"].append(dict(kwargs))
        if calls["count"] == 1:
            raise RuntimeError("simulated strategic failure")
        return json.dumps(["after_retry"])

    monkeypatch.setattr(qp_mod, "create_chat_completion", flaky_create_chat_completion)
    monkeypatch.setattr(qp_mod.json_repair, "loads", json.loads)

    res = await qp_mod.generate_sub_queries(
        query="Q2",
        parent_query="P2",
        report_type="R2",
        context=[],
        cfg=cfg,
        cost_callback=None,
        prompt_family=DummyPromptFamily,
    )

    assert res == ["after_retry"]
    # First call should have included reasoning_effort (and no max_tokens)
    assert "reasoning_effort" in calls["history"][0]
    # max_tokens may be absent or None on first call
    assert calls["history"][0].get("max_tokens") in (None, )
    # Second call should specify max_tokens equal to strategic_token_limit
    assert calls["history"][1].get("max_tokens") == cfg.strategic_token_limit


@pytest.mark.asyncio
async def test_generate_sub_queries_fallback_to_smart(monkeypatch):
    import importlib

    qp_mod = importlib.import_module("gpt_researcher.actions.query_processing")

    class DummyPromptFamily:
        @staticmethod
        def generate_search_queries_prompt(query, parent_query, report_type, max_iterations, context):
            return "FALLBACK_PROMPT"

    cfg = SimpleNamespace(
        max_iterations=2,
        strategic_llm_model="strat-x",
        strategic_llm_provider="prov-x",
        llm_kwargs={},
        strategic_token_limit=7,
        smart_llm_model="smart-x",
        smart_token_limit=55,
        smart_llm_provider="prov-smart",
        temperature=0.33,
    )

    calls = {"count": 0, "history": []}

    async def always_flaky_then_succeed(*args, **kwargs):
        calls["count"] += 1
        calls["history"].append(dict(kwargs))
        # fail twice, succeed third time
        if calls["count"] < 3:
            raise RuntimeError(f"simulated failure {calls['count']}")
        return json.dumps(["fallbacked"])

    monkeypatch.setattr(qp_mod, "create_chat_completion", always_flaky_then_succeed)
    monkeypatch.setattr(qp_mod.json_repair, "loads", json.loads)

    res = await qp_mod.generate_sub_queries(
        query="Q3",
        parent_query="P3",
        report_type="R3",
        context=None,
        cfg=cfg,
        cost_callback=None,
        prompt_family=DummyPromptFamily,
    )

    assert res == ["fallbacked"]
    # There should have been three attempts: initial strategic, retry strategic with max_tokens,
    # then fallback to smart model
    assert len(calls["history"]) == 3
    third = calls["history"][2]
    assert third.get("model") == cfg.smart_llm_model
    assert third.get("max_tokens") == cfg.smart_token_limit
    assert third.get("temperature") == cfg.temperature
