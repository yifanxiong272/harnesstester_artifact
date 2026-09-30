import asyncio
import os
import pytest

from gpt_researcher.utils import llm as llm_module
from gpt_researcher.utils.llm import create_chat_completion


class FakeProvider:
    def __init__(self, responses, raise_exc=False):
        # responses: list of values or Exception instances to raise
        self._responses = list(responses)
        self._i = 0
        self.last_response_metadata = {"meta": "ok"}
        self.last_usage_metadata = {"usage": "ok"}

    async def get_chat_response(self, messages, stream, websocket, **kwargs):
        # return or raise according to sequence
        if self._i >= len(self._responses):
            # keep returning last value
            val = self._responses[-1]
        else:
            val = self._responses[self._i]
        # advance index (but don't overflow)
        if self._i < len(self._responses) - 1:
            self._i += 1
        if isinstance(val, Exception):
            raise val
        return val


@pytest.mark.asyncio
async def test_model_none_round_031():
    # model None should raise ValueError early (line ~71-72)
    with pytest.raises(ValueError):
        await create_chat_completion(messages=[{"role": "user", "content": "hi"}], model=None)


@pytest.mark.asyncio
async def test_provider_kwargs_and_cost_and_openai_base_round_031(monkeypatch):
    # Test that llm_kwargs merges, reasoning_effort gets set for supported models,
    # openai base url is attached when llm_provider == 'openai', and cost_callback called.
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.test")

    captured_provider_kwargs = {}

    def fake_get_llm(llm_provider, **provider_kwargs):
        # store what was passed for assertions
        captured_provider_kwargs.update(provider_kwargs)
        return FakeProvider(["response_ok"])

    monkeypatch.setattr(llm_module, "get_llm", fake_get_llm)
    # ensure model 'm1' supports reasoning effort
    monkeypatch.setattr(llm_module, "SUPPORT_REASONING_EFFORT_MODELS", {"m1"})
    monkeypatch.setattr(llm_module, "NO_SUPPORT_TEMPERATURE_MODELS", set())

    # make calculate_llm_cost deterministic
    def fake_calculate_llm_cost(**kwargs):
        return {"cost": 0.42, "details": kwargs}

    monkeypatch.setattr(llm_module, "calculate_llm_cost", fake_calculate_llm_cost)

    seen_cost = {}

    def cost_cb(cost):
        seen_cost.update(cost)

    # patch asyncio.sleep to avoid delays if any
    async def _no_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    resp = await create_chat_completion(
        messages=[{"role": "user", "content": "hello"}],
        model="m1",
        temperature=0.2,
        max_tokens=123,
        llm_provider="openai",
        llm_kwargs={"extra": 1},
        cost_callback=cost_cb,
    )

    assert resp == "response_ok"
    # cost callback should have been called with our fake cost dict
    assert seen_cost.get("cost") == 0.42
    # provider kwargs should include merged llm_kwargs
    assert captured_provider_kwargs.get("extra") == 1
    # reasoning_effort should be set because model is in SUPPORT_REASONING_EFFORT_MODELS
    assert "reasoning_effort" in captured_provider_kwargs
    # temperature and max_tokens should be present because model supports temperature
    assert captured_provider_kwargs.get("temperature") == 0.2
    assert captured_provider_kwargs.get("max_tokens") == 123
    # openai base URL should have been attached when llm_provider == 'openai'
    assert captured_provider_kwargs.get("openai_api_base") == "https://api.test"


@pytest.mark.asyncio
async def test_no_temperature_models_round_031(monkeypatch):
    # If model is in NO_SUPPORT_TEMPERATURE_MODELS then temperature and max_tokens are set to None
    captured_provider_kwargs = {}

    def fake_get_llm(llm_provider, **provider_kwargs):
        captured_provider_kwargs.update(provider_kwargs)
        return FakeProvider(["ok"])

    monkeypatch.setattr(llm_module, "get_llm", fake_get_llm)
    monkeypatch.setattr(llm_module, "SUPPORT_REASONING_EFFORT_MODELS", set())
    monkeypatch.setattr(llm_module, "NO_SUPPORT_TEMPERATURE_MODELS", {"m_no_temp"})

    # patch sleep to no-op to be safe
    async def _no_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    resp = await create_chat_completion(
        messages=[{"role": "user", "content": "q"}],
        model="m_no_temp",
        temperature=0.9,
        max_tokens=999,
    )

    assert resp == "ok"
    # temperature and max_tokens should be explicitly set to None for models that don't support them
    assert captured_provider_kwargs.get("temperature") is None
    assert captured_provider_kwargs.get("max_tokens") is None


@pytest.mark.asyncio
async def test_retries_and_final_runtime_error_round_031(monkeypatch):
    # Simulate provider that always raises exceptions -> final RuntimeError after retries (lines ~109-149).
    def fake_get_llm(llm_provider, **provider_kwargs):
        return FakeProvider([Exception("boom")] * 3)

    monkeypatch.setattr(llm_module, "get_llm", fake_get_llm)
    monkeypatch.setattr(llm_module, "SUPPORT_REASONING_EFFORT_MODELS", set())
    monkeypatch.setattr(llm_module, "NO_SUPPORT_TEMPERATURE_MODELS", set())

    # speed up sleep
    async def _no_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    with pytest.raises(RuntimeError) as excinfo:
        await create_chat_completion(
            messages=[{"role": "user", "content": "a"}],
            model="m3",
            llm_provider="prov_name",
        )

    # The raised RuntimeError should mention the provider name
    assert "prov_name" in str(excinfo.value)


@pytest.mark.asyncio
async def test_empty_then_success_cost_callback_round_031(monkeypatch):
    # Simulate empty response first (triggers empty-response branch and retry), then success
    seq = ["", "final_answer"]
    provider = FakeProvider(seq)

    def fake_get_llm(llm_provider, **provider_kwargs):
        # return the same provider instance so last_response_metadata is available
        return provider

    monkeypatch.setattr(llm_module, "get_llm", fake_get_llm)
    monkeypatch.setattr(llm_module, "SUPPORT_REASONING_EFFORT_MODELS", set())
    monkeypatch.setattr(llm_module, "NO_SUPPORT_TEMPERATURE_MODELS", set())

    # deterministic cost calculator
    def fake_calculate_llm_cost(**kwargs):
        return {"called": True, "model": kwargs.get("model")}

    monkeypatch.setattr(llm_module, "calculate_llm_cost", fake_calculate_llm_cost)

    seen = {}

    def cb(cost):
        seen.update(cost)

    async def _no_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    resp = await create_chat_completion(
        messages=[{"role": "user", "content": "check"}],
        model="m_ok",
        cost_callback=cb,
    )

    assert resp == "final_answer"
    # cost callback should have been called with our fake cost data
    assert seen.get("called") is True
    assert seen.get("model") == "m_ok"
