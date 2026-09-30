import pytest
from types import SimpleNamespace

import asyncio

from gpt_researcher.actions import query_processing


class FakePromptFamily:
    @staticmethod
    def generate_search_queries_prompt(query, parent_query, report_type, max_iterations, context):
        # Preserve payload shape and reflect inputs for deterministic checks
        return f"PROMPT|{query}|{parent_query}|{report_type}|{max_iterations}|{context}"


class DummyConfig:
    def __init__(self):
        # attributes referenced by generate_sub_queries
        self.max_iterations = None
        self.strategic_llm_model = "strategic-model"
        self.strategic_llm_provider = "strategic-provider"
        self.llm_kwargs = {"kw": "v"}
        self.strategic_token_limit = 42
        self.smart_llm_model = "smart-model"
        self.temperature = 0.12
        self.smart_token_limit = 7
        self.smart_llm_provider = "smart-provider"


@pytest.mark.asyncio
async def test_generate_sub_queries_success_round_100(monkeypatch):
    """
    Successful first-call path: covers prompt generation (line ~63) and first await (lines ~71-81)
    """
    cfg = DummyConfig()

    # Track calls and ensure the initial call uses max_tokens=None
    calls = []

    async def fake_create_chat_completion(*args, **kwargs):
        calls.append((args, kwargs))
        # Return a deterministic string that json_repair.loads will be patched to translate
        return 'RESULT_OK'

    # Patch the create function where the module resolves it
    monkeypatch.setattr(query_processing, "create_chat_completion", fake_create_chat_completion)

    # Patch json_repair.loads to be deterministic and observable
    loaded = {}

    def fake_loads(resp):
        loaded['value'] = resp
        # Emulate a repaired/parsed structure
        return ["parsed", resp]

    monkeypatch.setattr(query_processing.json_repair, "loads", fake_loads)

    result = await query_processing.generate_sub_queries(
        query="q1",
        parent_query="pq",
        report_type="report",
        context=[{"k": "v"}],
        cfg=cfg,
        cost_callback=None,
        prompt_family=FakePromptFamily,
    )

    # Assertions: function returned the patched json_repair.loads value
    assert result == ["parsed", "RESULT_OK"]

    # The prompt was constructed with the expected inputs (covers line 63 behavior)
    # Check that create_chat_completion was called once and with max_tokens explicitly set to None
    assert len(calls) == 1
    _, kwargs = calls[0]
    assert kwargs.get("max_tokens") is None


@pytest.mark.asyncio
async def test_retry_with_strategic_token_limit_round_100(monkeypatch):
    """
    Simulate first create_chat_completion raising, then retry succeeding with max_tokens=strategic_token_limit
    Covers exception handling (lines ~82-96) and the successful retry branch.
    """
    cfg = DummyConfig()

    # Prepare behavior: first call raises, second call returns a sentinel
    behaviors = [Exception("first-fail"), "RETRY_OK"]
    calls = []

    async def fake_create_chat_completion(*args, **kwargs):
        calls.append((args, kwargs))
        behavior = behaviors.pop(0)
        if isinstance(behavior, Exception):
            raise behavior
        return behavior

    monkeypatch.setattr(query_processing, "create_chat_completion", fake_create_chat_completion)

    seen = {}

    def fake_loads(resp):
        seen['resp'] = resp
        return ["after-retry", resp]

    monkeypatch.setattr(query_processing.json_repair, "loads", fake_loads)

    result = await query_processing.generate_sub_queries(
        query="q2",
        parent_query="pq2",
        report_type="r2",
        context=[],
        cfg=cfg,
        prompt_family=FakePromptFamily,
    )

    # After a single retry we should have a parsed result from the second call
    assert result == ["after-retry", "RETRY_OK"]

    # Two calls: first raised (no max_tokens), second used strategic_token_limit
    assert len(calls) == 2
    _, first_kwargs = calls[0]
    _, second_kwargs = calls[1]
    # first call explicitly passes max_tokens=None per implementation
    assert first_kwargs.get("max_tokens") is None
    # second call should pass the configured strategic token limit
    assert second_kwargs.get("max_tokens") == cfg.strategic_token_limit


@pytest.mark.asyncio
async def test_fallback_to_smart_llm_round_100(monkeypatch):
    """
    Simulate both the first and the retry raising, forcing the fallback to the smart model (lines ~96-107).
    Assert that the fallback call uses smart model, smart token limit and temperature.
    """
    cfg = DummyConfig()

    # Prepare behavior: first two calls raise, third returns value
    behaviors = [Exception("first"), Exception("second"), "SMART_OK"]
    calls = []

    async def fake_create_chat_completion(*args, **kwargs):
        # record positional and keyword args for inspection
        calls.append((args, kwargs))
        behavior = behaviors.pop(0)
        if isinstance(behavior, Exception):
            raise behavior
        return behavior

    monkeypatch.setattr(query_processing, "create_chat_completion", fake_create_chat_completion)

    recorded = {}

    def fake_loads(resp):
        recorded['resp'] = resp
        return {"final": resp}

    monkeypatch.setattr(query_processing.json_repair, "loads", fake_loads)

    result = await query_processing.generate_sub_queries(
        query="q3",
        parent_query="pq3",
        report_type="r3",
        context=[{}],
        cfg=cfg,
        prompt_family=FakePromptFamily,
    )

    # The final return should be the json_repair.loads output for the SMART_OK response
    assert result == {"final": "SMART_OK"}

    # Three calls were attempted (strategic initial, strategic retry, fallback smart)
    assert len(calls) == 3

    # Inspect the third call's kwargs to ensure fallback parameters are used
    _, third_kwargs = calls[2]
    # The fallback should have used the smart llm model and smart token limit and provided temperature
    # Model is a positional or keyword argument; check kwargs first, then args for model
    third_args, _ = calls[2]
    # The code sets model=cfg.smart_llm_model as a keyword in the call; verify via kwargs
    assert third_kwargs.get("model") == cfg.smart_llm_model
    assert third_kwargs.get("max_tokens") == cfg.smart_token_limit
    assert third_kwargs.get("temperature") == cfg.temperature
