# file: gpt_researcher/utils/llm.py:41-149
# asked: {"lines": [72, 87, 90, 96, 97, 100, 101, 102, 114, 115, 116, 117, 119, 120, 121, 122, 125, 126, 127, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 148, 149], "branches": [[71, 72], [86, 87], [89, 90], [92, 96], [99, 100], [101, 102], [101, 104], [109, 148], [119, 120], [119, 122], [124, 125], [129, 130], [129, 132], [134, 135]]}
# gained: {"lines": [72, 87, 90, 96, 97, 100, 101, 102, 114, 115, 116, 117, 119, 120, 121, 125, 126, 127, 129, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 148, 149], "branches": [[71, 72], [86, 87], [89, 90], [92, 96], [99, 100], [101, 102], [119, 120], [124, 125], [129, 132], [134, 135]]}

import asyncio
import types
import pytest

from gpt_researcher.utils import llm as llm_mod
from gpt_researcher.llm_provider.generic.base import SUPPORT_REASONING_EFFORT_MODELS, NO_SUPPORT_TEMPERATURE_MODELS


@pytest.mark.asyncio
async def test_model_none_raises():
    with pytest.raises(ValueError, match="Model cannot be None"):
        await llm_mod.create_chat_completion(messages=[{"role": "user", "content": "hi"}], model=None)


@pytest.mark.asyncio
async def test_max_tokens_too_big_raises():
    with pytest.raises(ValueError, match="max_tokens=300000 exceeds the largest output limit"):
        await llm_mod.create_chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            model="some-model",
            max_tokens=300_000,
        )


@pytest.mark.asyncio
async def test_llm_kwargs_update_reasoning_and_openai_base_and_cost_callback(monkeypatch):
    captured_kwargs = {}

    # Ensure we pick a model that supports reasoning effort
    model = SUPPORT_REASONING_EFFORT_MODELS[0]

    async def fake_get_chat_response(messages, stream, websocket, **kwargs):
        return "the-response"

    class FakeProvider:
        def __init__(self):
            self.last_response_metadata = {"meta": "resp"}
            self.last_usage_metadata = {"usage": 1}

        async def get_chat_response(self, messages, stream, websocket, **kwargs):
            return await fake_get_chat_response(messages, stream, websocket, **kwargs)

    def fake_get_llm(llm_provider, **kwargs):
        # capture kwargs passed to provider factory
        captured_kwargs.update(kwargs)
        return FakeProvider()

    # patch get_llm and calculate_llm_cost
    monkeypatch.setattr(llm_mod, "get_llm", fake_get_llm)

    # Provide a fake calculate_llm_cost that returns a dict
    def fake_calculate_llm_cost(**kwargs):
        return {"cost": 0.42, "info": kwargs}

    monkeypatch.setattr(llm_mod, "calculate_llm_cost", fake_calculate_llm_cost)

    # Set OPENAI_BASE_URL to ensure branch that adds openai_api_base is exercised
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.test")

    # capture cost callback calls
    captured_cost = {}

    def cost_callback(costs):
        captured_cost.update(costs)

    # Provide some llm_kwargs to force provider_kwargs.update(llm_kwargs)
    llm_kwargs = {"extra_arg": "value"}

    response = await llm_mod.create_chat_completion(
        messages=[{"role": "user", "content": "hello"}],
        model=model,
        llm_provider="openai",
        llm_kwargs=llm_kwargs,
        cost_callback=cost_callback,
    )

    assert response == "the-response"
    # llm_kwargs should have been merged
    assert captured_kwargs.get("extra_arg") == "value"
    # reasoning_effort should be present for models in SUPPORT_REASONING_EFFORT_MODELS
    assert "reasoning_effort" in captured_kwargs
    # Because this model is listed in NO_SUPPORT_TEMPERATURE_MODELS, temperature/max_tokens should be None
    assert captured_kwargs.get("temperature") is None
    assert captured_kwargs.get("max_tokens") is None
    # openai base should be forwarded
    assert captured_kwargs.get("openai_api_base") == "https://api.openai.test"
    # cost callback should have been called via calculate_llm_cost return value
    assert captured_cost.get("cost") == 0.42


@pytest.mark.asyncio
async def test_temperature_assigned_for_supported_model(monkeypatch):
    captured_kwargs = {}

    # Choose a model that is NOT in NO_SUPPORT_TEMPERATURE_MODELS
    model = "gpt-x-test-model"
    assert model not in NO_SUPPORT_TEMPERATURE_MODELS

    class Provider:
        last_response_metadata = {}
        last_usage_metadata = {}

        async def get_chat_response(self, messages, stream, websocket, **kwargs):
            return "ok"

    def fake_get_llm(llm_provider, **kwargs):
        captured_kwargs.update(kwargs)
        return Provider()

    monkeypatch.setattr(llm_mod, "get_llm", fake_get_llm)

    response = await llm_mod.create_chat_completion(
        messages=[{"role": "user", "content": "hi"}],
        model=model,
        temperature=0.9,
        max_tokens=1234,
    )

    assert response == "ok"
    # temperature and max_tokens should be forwarded
    assert captured_kwargs.get("temperature") == 0.9
    assert captured_kwargs.get("max_tokens") == 1234


@pytest.mark.asyncio
async def test_retry_on_exception_then_success(monkeypatch):
    # This test will make provider raise twice then succeed to cover the retry & sleep logic.
    calls = {"count": 0}
    sleep_calls = []

    async def fake_sleep(delay):
        sleep_calls.append(delay)
        # don't actually sleep

    # Patch asyncio.sleep used inside the module
    monkeypatch.setattr(llm_mod.asyncio, "sleep", fake_sleep)

    class Provider:
        last_response_metadata = {}
        last_usage_metadata = {}

        async def get_chat_response(self, messages, stream, websocket, **kwargs):
            calls["count"] += 1
            if calls["count"] <= 2:
                raise RuntimeError(f"transient-{calls['count']}")
            return "final"

    def fake_get_llm(llm_provider, **kwargs):
        return Provider()

    monkeypatch.setattr(llm_mod, "get_llm", fake_get_llm)

    # call with default max_attempts (10) so it will retry
    response = await llm_mod.create_chat_completion(
        messages=[{"role": "user", "content": "retry"}],
        model="retry-model",
    )

    assert response == "final"
    # ensure we retried (two failures then success => count == 3)
    assert calls["count"] == 3
    # sleep should have been called at least twice (for attempt1 and attempt2 failures)
    assert len(sleep_calls) >= 2
    # sleep intervals should be powers of two capped at 8; first calls are 1,2
    assert sleep_calls[0] == 1 or pytest.approx(sleep_calls[0]) == 1
    assert sleep_calls[1] == 2 or pytest.approx(sleep_calls[1]) == 2


@pytest.mark.asyncio
async def test_empty_response_with_stream_raises(monkeypatch):
    # Use stream=True and websocket provided to set max_attempts=1 so we hit empty-response branch and exit quickly
    class Provider:
        last_response_metadata = {}
        last_usage_metadata = {}

        async def get_chat_response(self, messages, stream, websocket, **kwargs):
            return ""  # empty response exercises the empty-response handling

    def fake_get_llm(llm_provider, **kwargs):
        return Provider()

    monkeypatch.setattr(llm_mod, "get_llm", fake_get_llm)

    with pytest.raises(RuntimeError) as excinfo:
        await llm_mod.create_chat_completion(
            messages=[{"role": "user", "content": "empty"}],
            model="anything",
            stream=True,
            websocket=object(),  # non-None so max_attempts == 1
        )

    # The raised RuntimeError should wrap the Empty response runtime error as its __cause__
    assert "Failed to get response from" in str(excinfo.value)
    cause = excinfo.value.__cause__
    assert isinstance(cause, RuntimeError)
    assert "Empty response from LLM provider" in str(cause)
