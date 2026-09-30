# file: gpt_researcher/actions/report_generation.py:115-157
# asked: {"lines": [138, 139, 140, 141, 142, 143, 145, 146, 147, 148, 149, 150, 151, 152, 154, 155, 156, 157], "branches": []}
# gained: {"lines": [138, 139, 140, 141, 142, 143, 145, 146, 147, 148, 149, 150, 151, 152, 154, 155, 156, 157], "branches": []}

import importlib
import pytest

@pytest.mark.asyncio
async def test_summarize_url_success(monkeypatch):
    module = importlib.import_module("gpt_researcher.actions.report_generation")

    recorded = {}

    async def fake_create_chat_completion(**kwargs):
        # record kwargs for assertions and simulate async return
        recorded.update(kwargs)
        return "MOCK_SUMMARY"

    # Patch the create_chat_completion used inside summarize_url
    monkeypatch.setattr(module, "create_chat_completion", fake_create_chat_completion)

    # Create a minimal config-like object with required attributes
    class DummyConfig:
        pass

    config = DummyConfig()
    config.smart_llm_model = "test-model"
    config.smart_llm_provider = "test-provider"
    config.smart_token_limit = 999
    config.llm_kwargs = {"opt": True}

    url = "http://example.test/page"
    content = "Important content to summarize."
    role = "tester-role"
    websocket = object()

    async def cost_callback(*a, **k):
        return "cost-called"

    # Call the function under test
    result = await module.summarize_url(
        url,
        content,
        role,
        config,
        websocket=websocket,
        cost_callback=cost_callback,
        extra_flag=123,
    )

    # Assertions: ensure returned summary and that create_chat_completion was called with expected args
    assert result == "MOCK_SUMMARY"
    assert recorded["model"] == config.smart_llm_model
    assert recorded["temperature"] == 0.25
    assert recorded["llm_provider"] == config.smart_llm_provider
    assert recorded["stream"] is True
    assert recorded["websocket"] is websocket
    assert recorded["max_tokens"] == config.smart_token_limit
    assert recorded["llm_kwargs"] == config.llm_kwargs
    assert recorded["cost_callback"] is cost_callback
    assert recorded["extra_flag"] == 123

    # Messages content checks
    msgs = recorded["messages"]
    assert isinstance(msgs, list)
    # system role with role content
    assert any(m.get("role") == "system" and m.get("content") == role for m in msgs)
    # user message contains url and content
    assert any(
        m.get("role") == "user"
        and f"Summarize the following content from {url}:" in m.get("content", "")
        and content in m.get("content", "")
        for m in msgs
    )


@pytest.mark.asyncio
async def test_summarize_url_exception_logs_and_returns_empty(monkeypatch):
    module = importlib.import_module("gpt_researcher.actions.report_generation")

    async def fake_create_chat_completion(*args, **kwargs):
        raise RuntimeError("simulated failure")

    # Patch the create_chat_completion to raise
    monkeypatch.setattr(module, "create_chat_completion", fake_create_chat_completion)

    # Replace logger with a dummy that records error calls
    errors = []

    class DummyLogger:
        def error(self, msg):
            errors.append(msg)

    monkeypatch.setattr(module, "logger", DummyLogger())

    # Minimal config object
    class DummyConfig:
        pass

    config = DummyConfig()
    config.smart_llm_model = "m"
    config.smart_llm_provider = "p"
    config.smart_token_limit = 1
    config.llm_kwargs = {}

    # Call the function under test; should catch exception and return empty string
    result = await module.summarize_url(
        "http://x", "c", "r", config, websocket=None, cost_callback=None
    )

    assert result == ""
    # Ensure logger.error was called and contains the expected prefix
    assert errors, "logger.error was not called on exception"
    assert any("Error in summarizing URL" in e for e in errors)
