import os
import asyncio
import types
import pytest

from gpt_researcher.utils import llm as llm_mod

# Helper to create a dummy async sleep so tests don't actually wait
async def _dummy_sleep(_):
    return None


def test_model_none_round_031():
    """Calling create_chat_completion with model=None should raise ValueError."""
    messages = [{"role": "user", "content": "hello"}]
    with pytest.raises(ValueError) as exc:
        asyncio.run(
            llm_mod.create_chat_completion(messages=messages, model=None)
        )
    assert "Model cannot be None" in str(exc.value)


def test_max_tokens_too_large_round_031():
    """max_tokens above 200_000 triggers a ValueError guard."""
    messages = [{"role": "user", "content": "hello"}]
    with pytest.raises(ValueError) as exc:
        asyncio.run(
            llm_mod.create_chat_completion(messages=messages, model="m1", max_tokens=300_000)
        )
    assert "max_tokens=300000" in str(exc.value) or "exceeds" in str(exc.value)


def test_success_with_cost_callback_round_031(monkeypatch):
    """When provider returns a non-empty response: ensure provider kwargs updated from llm_kwargs,
    reasoning_effort added for supported models, temperature and max_tokens set, and cost_callback invoked."""
    # Arrange
    messages = [{"role": "user", "content": "hi"}]

    # Control the model support sets so we exercise the reasoning_effort branch
    monkeypatch.setattr(llm_mod, "SUPPORT_REASONING_EFFORT_MODELS", {"reason-model"})
    monkeypatch.setattr(llm_mod, "NO_SUPPORT_TEMPERATURE_MODELS", set())

    # Provide a fake provider whose get_chat_response returns a known string
    class FakeProvider:
        def __init__(self):
            self.last_response_metadata = {"meta": "v"}
            self.last_usage_metadata = {"usage": 1}

        async def get_chat_response(self, messages_arg, stream_arg, websocket_arg, **kwargs):
            # validate forwarded args are as expected (deterministic checks)
            assert messages_arg == messages
            return "THE_RESPONSE"

    fake_provider = FakeProvider()

    # Capture the kwargs that get_llm receives to ensure llm_kwargs were merged
    captured_provider_kwargs = {}

    def fake_get_llm(llm_provider_arg, **provider_kwargs):
        captured_provider_kwargs.update(provider_kwargs)
        return fake_provider

    monkeypatch.setattr(llm_mod, "get_llm", fake_get_llm)

    # Replace calculate_llm_cost with deterministic function
    def fake_calculate_llm_cost(**kwargs):
        # ensure we receive the provider metadata items
        assert "response_metadata" in kwargs
        return {"cost": 0.42}

    monkeypatch.setattr(llm_mod, "calculate_llm_cost", fake_calculate_llm_cost)

    # Avoid sleeping delays in retry logic (even though it shouldn't be used here)
    monkeypatch.setattr(asyncio, "sleep", _dummy_sleep)

    got_costs = []

    def cost_cb(cost_dict):
        got_costs.append(cost_dict)

    # Act
    result = asyncio.run(
        llm_mod.create_chat_completion(
            messages=messages,
            model="reason-model",
            temperature=0.1,
            max_tokens=10,
            llm_kwargs={"extra": "value"},
            cost_callback=cost_cb,
        )
    )

    # Assert
    assert result == "THE_RESPONSE"
    # llm_kwargs should have been merged into provider kwargs
    assert captured_provider_kwargs.get("extra") == "value"
    # reasoning_effort should have been added because model is in SUPPORT_REASONING_EFFORT_MODELS
    assert captured_provider_kwargs.get("reasoning_effort") == llm_mod.ReasoningEfforts.Medium.value
    # temperature and max_tokens should be present for this model
    assert captured_provider_kwargs.get("temperature") == 0.1
    assert captured_provider_kwargs.get("max_tokens") == 10
    # cost_callback should have been called with the deterministic cost dict
    assert got_costs == [{"cost": 0.42}]


def test_openai_base_and_no_temperature_round_031(monkeypatch):
    """When llm_provider == 'openai' and the model is in NO_SUPPORT_TEMPERATURE_MODELS,
    ensure openai_api_base is pulled from env and temperature/max_tokens set to None.
    """
    messages = [{"role": "user", "content": "ping"}]

    monkeypatch.setattr(llm_mod, "NO_SUPPORT_TEMPERATURE_MODELS", {"no-temp-model"})
    monkeypatch.setattr(llm_mod, "SUPPORT_REASONING_EFFORT_MODELS", set())

    # Ensure OPENAI_BASE_URL env var is present
    monkeypatch.setenv("OPENAI_BASE_URL", "http://openai-base.local")

    class FakeProvider2:
        def __init__(self):
            self.last_response_metadata = None
            self.last_usage_metadata = None

        async def get_chat_response(self, messages_arg, stream_arg, websocket_arg, **kwargs):
            return "OK_NO_TEMP"

    fake_provider2 = FakeProvider2()

    # Create a fake get_llm that asserts provider_kwargs content
    def fake_get_llm_openai(llm_provider_arg, **provider_kwargs):
        # Should be called with openai_api_base set from env
        assert provider_kwargs.get("openai_api_base") == "http://openai-base.local"
        # For models that do not support temperature, temperature and max_tokens should be None
        assert provider_kwargs.get("temperature") is None
        assert provider_kwargs.get("max_tokens") is None
        return fake_provider2

    monkeypatch.setattr(llm_mod, "get_llm", fake_get_llm_openai)
    monkeypatch.setattr(asyncio, "sleep", _dummy_sleep)

    result = asyncio.run(
        llm_mod.create_chat_completion(
            messages=messages,
            model="no-temp-model",
            llm_provider="openai",
        )
    )
    assert result == "OK_NO_TEMP"


def test_provider_always_raises_round_031(monkeypatch):
    """If the provider continually raises exceptions, create_chat_completion should
    exhaust attempts and finally raise RuntimeError.
    """
    messages = [{"role": "user", "content": "fail"}]

    class BrokenProvider:
        def __init__(self):
            self.last_response_metadata = None
            self.last_usage_metadata = None

        async def get_chat_response(self, *args, **kwargs):
            raise RuntimeError("boom")

    broken = BrokenProvider()

    def fake_get_llm_broken(llm_provider_arg, **provider_kwargs):
        return broken

    monkeypatch.setattr(llm_mod, "get_llm", fake_get_llm_broken)
    # Prevent actual sleeping delays
    monkeypatch.setattr(asyncio, "sleep", _dummy_sleep)

    with pytest.raises(RuntimeError):
        asyncio.run(
            llm_mod.create_chat_completion(
                messages=messages,
                model="some-model",
            )
        )
