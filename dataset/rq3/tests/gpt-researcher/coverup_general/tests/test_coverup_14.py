# file: gpt_researcher/utils/llm.py:41-149
# asked: {"lines": [72, 87, 90, 96, 97, 100, 101, 102, 114, 115, 116, 117, 119, 120, 121, 122, 125, 126, 127, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 148, 149], "branches": [[71, 72], [86, 87], [89, 90], [92, 96], [99, 100], [101, 102], [101, 104], [109, 148], [119, 120], [119, 122], [124, 125], [129, 130], [129, 132], [134, 135]]}
# gained: {"lines": [72, 87, 90, 96, 97, 100, 101, 102, 114, 115, 116, 117, 119, 120, 121, 125, 126, 127, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 148, 149], "branches": [[71, 72], [86, 87], [89, 90], [92, 96], [99, 100], [101, 102], [119, 120], [124, 125], [129, 130], [129, 132], [134, 135]]}

import asyncio
import os
import pytest

# Try the most likely import paths for the module under test.
try:
    from gpt_researcher.utils import llm as llm_module
except Exception:
    from gpt_researcher.gpt_researcher.utils import llm as llm_module


class FakeProvider:
    def __init__(self, sequence, last_response_metadata=None, last_usage_metadata=None):
        """
        sequence: list where each element is either:
          - Exception instance to be raised
          - string response to be returned (may be empty)
        """
        self._sequence = list(sequence)
        self.last_response_metadata = last_response_metadata or {"meta": "resp"}
        self.last_usage_metadata = last_usage_metadata or {"usage": "meta"}

    async def get_chat_response(self, messages, stream, websocket, **kwargs):
        if not self._sequence:
            # default to empty response if sequence exhausted
            return ""
        next_item = self._sequence.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return next_item


@pytest.mark.asyncio
async def test_model_none_raises_value_error():
    # model is None should raise ValueError (line 72)
    with pytest.raises(ValueError) as excinfo:
        await llm_module.create_chat_completion(messages=[{"role": "user", "content": "hi"}], model=None)
    assert "Model cannot be None" in str(excinfo.value)


@pytest.mark.asyncio
async def test_llm_kwargs_reasoning_and_openai_base_and_cost_callback(monkeypatch):
    # Prepare environment and module-level sets
    model_name = "reason-model"
    monkeypatch.setenv("OPENAI_BASE_URL", "https://custom-openai.example")
    monkeypatch.setattr(llm_module, "SUPPORT_REASONING_EFFORT_MODELS", {model_name})
    monkeypatch.setattr(llm_module, "NO_SUPPORT_TEMPERATURE_MODELS", set())

    captured_provider_kwargs = {}

    # Fake get_llm that captures kwargs and returns a provider that replies normally
    def fake_get_llm(llm_provider, **provider_kwargs):
        # Capture for assertions
        captured_provider_kwargs.update(provider_kwargs)
        # Ensure model and llm_kwargs merged, reasoning_effort present, and openai_api_base set
        assert provider_kwargs["model"] == model_name
        assert provider_kwargs.get("custom_key") == "custom_value"
        assert provider_kwargs.get("reasoning_effort") == "high-effort"
        # temperature should be preserved (not in NO_SUPPORT_TEMPERATURE_MODELS)
        assert provider_kwargs.get("temperature") is not None
        assert provider_kwargs.get("max_tokens") == 4000
        # OPENAI_BASE_URL should be added for openai provider
        assert provider_kwargs.get("openai_api_base") == "https://custom-openai.example"
        return FakeProvider(["the-response"])

    monkeypatch.setattr(llm_module, "get_llm", fake_get_llm)

    # Fake cost calculation and a callback to capture the cost passed
    called_costs = []

    def fake_calculate(**kwargs):
        # verify some of the passed options exist
        assert kwargs["llm_provider"] == "openai"
        assert kwargs["model"] == model_name
        return {"cost": 0.42}

    def cost_callback(cost):
        called_costs.append(cost)

    monkeypatch.setattr(llm_module, "calculate_llm_cost", fake_calculate)

    # Make sleep a no-op to speed tests if any retry/backoff were to occur
    async def noop_sleep(_):
        return None

    monkeypatch.setattr(llm_module.asyncio, "sleep", noop_sleep)

    # Call the function under test
    resp = await llm_module.create_chat_completion(
        messages=[{"role": "user", "content": "hello"}],
        model=model_name,
        llm_provider="openai",
        llm_kwargs={"custom_key": "custom_value"},
        reasoning_effort="high-effort",
        cost_callback=cost_callback,
    )

    assert resp == "the-response"
    assert called_costs == [{"cost": 0.42}]
    # Confirm provider kwargs captured
    assert captured_provider_kwargs["custom_key"] == "custom_value"
    assert captured_provider_kwargs["reasoning_effort"] == "high-effort"
    assert captured_provider_kwargs["openai_api_base"] == "https://custom-openai.example"


@pytest.mark.asyncio
async def test_no_temperature_support_sets_none(monkeypatch):
    # Model that does not support temperature should have temperature and max_tokens set to None
    model_name = "no-temp-model"
    monkeypatch.setattr(llm_module, "NO_SUPPORT_TEMPERATURE_MODELS", {model_name})
    monkeypatch.setattr(llm_module, "SUPPORT_REASONING_EFFORT_MODELS", set())

    captured_provider_kwargs = {}

    def fake_get_llm(llm_provider, **provider_kwargs):
        captured_provider_kwargs.update(provider_kwargs)
        assert provider_kwargs["model"] == model_name
        assert provider_kwargs["temperature"] is None
        assert provider_kwargs["max_tokens"] is None
        return FakeProvider(["ok"])

    monkeypatch.setattr(llm_module, "get_llm", fake_get_llm)

    # Call function and assert normal response
    resp = await llm_module.create_chat_completion(
        messages=[{"role": "user", "content": "hi"}],
        model=model_name,
        llm_provider="some-provider",
    )
    assert resp == "ok"
    assert captured_provider_kwargs["temperature"] is None
    assert captured_provider_kwargs["max_tokens"] is None


@pytest.mark.asyncio
async def test_retry_on_exceptions_then_success_and_cost(monkeypatch):
    # Simulate provider raising exceptions twice then succeeding.
    model_name = "retry-model"
    monkeypatch.setattr(llm_module, "NO_SUPPORT_TEMPERATURE_MODELS", set())
    monkeypatch.setattr(llm_module, "SUPPORT_REASONING_EFFORT_MODELS", set())

    # Prepare provider that will raise twice then return a response
    provider = FakeProvider([Exception("boom1"), Exception("boom2"), "final"])

    def fake_get_llm(llm_provider, **provider_kwargs):
        # Return our provider instance regardless of kwargs
        return provider

    monkeypatch.setattr(llm_module, "get_llm", fake_get_llm)

    # Capture sleeps for exponential backoff (should be called at least twice)
    sleep_calls = []

    async def record_sleep(sec):
        sleep_calls.append(sec)
        return None

    monkeypatch.setattr(llm_module.asyncio, "sleep", record_sleep)

    # Fake cost calculation to verify cost_callback branch
    def fake_calculate(**kwargs):
        # Should receive the 'final' output
        assert kwargs["output_content"] == "final"
        return {"cost": 3.14}

    called_costs = []

    def cost_callback(cost):
        called_costs.append(cost)

    monkeypatch.setattr(llm_module, "calculate_llm_cost", fake_calculate)

    resp = await llm_module.create_chat_completion(
        messages=[{"role": "user", "content": "retry me"}],
        model=model_name,
        llm_provider="any",
        cost_callback=cost_callback,
    )

    assert resp == "final"
    # We expect at least two retries (two exceptions before success)
    assert len(sleep_calls) >= 2
    assert called_costs == [{"cost": 3.14}]


@pytest.mark.asyncio
async def test_empty_responses_exhaust_attempts_and_raise(monkeypatch):
    # Simulate provider always returning empty string -> should raise final RuntimeError
    model_name = "empty-model"
    monkeypatch.setattr(llm_module, "NO_SUPPORT_TEMPERATURE_MODELS", set())
    monkeypatch.setattr(llm_module, "SUPPORT_REASONING_EFFORT_MODELS", set())

    # provider that always returns empty string
    provider = FakeProvider(["", "", "", "", "", "", "", "", "", ""])  # ensure many empties

    def fake_get_llm(llm_provider, **provider_kwargs):
        return provider

    monkeypatch.setattr(llm_module, "get_llm", fake_get_llm)

    # Make sleep no-op (but record durations)
    sleep_calls = []

    async def record_sleep(sec):
        sleep_calls.append(sec)
        return None

    monkeypatch.setattr(llm_module.asyncio, "sleep", record_sleep)

    with pytest.raises(RuntimeError) as excinfo:
        await llm_module.create_chat_completion(
            messages=[{"role": "user", "content": "please reply"}],
            model=model_name,
            llm_provider="empty-provider",
        )

    # Confirm the outer error message mentions the provider and that there is a cause
    assert "Failed to get response from empty-provider API" in str(excinfo.value)
    # The RuntimeError should have a __cause__ which is the last_exception set inside function
    assert excinfo.value.__cause__ is not None
    assert isinstance(excinfo.value.__cause__, RuntimeError)
    assert "Empty response from LLM provider" in str(excinfo.value.__cause__)
    # Ensure we attempted some sleeps (retries)
    assert len(sleep_calls) >= 1
