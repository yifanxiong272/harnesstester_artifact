# file: gpt_researcher/actions/report_generation.py:63-112
# asked: {"lines": [88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 100, 101, 102, 103, 104, 105, 106, 107, 109, 110, 111, 112], "branches": []}
# gained: {"lines": [88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 100, 101, 102, 103, 104, 105, 106, 107, 109, 110, 111, 112], "branches": []}

import logging

import pytest


@pytest.mark.asyncio
async def test_write_conclusion_success(monkeypatch):
    # Import the module under test
    from gpt_researcher.actions import report_generation

    captured = {}

    async def fake_create_chat_completion(*args, **kwargs):
        # capture parameters for assertions
        captured['args'] = args
        captured['kwargs'] = kwargs
        return "Generated conclusion"

    # Patch the create_chat_completion in the module
    monkeypatch.setattr(report_generation, "create_chat_completion", fake_create_chat_completion)

    # Provide a fake PromptFamily with a deterministic generate_report_conclusion
    class FakePromptFamily:
        @staticmethod
        def generate_report_conclusion(query: str, report_content: str, language: str):
            return f"CONCLUDE: query={query}; content={report_content}; lang={language}"

    # Minimal config object with needed attributes
    class DummyConfig:
        smart_llm_model = "gpt-test"
        smart_llm_provider = "test-provider"
        language = "en"
        smart_token_limit = 123
        llm_kwargs = {"foo": "bar"}

    cfg = DummyConfig()
    query = "What is testing?"
    context = "Some report content."
    agent_role_prompt = "You are a helpful test agent."
    websocket = object()
    cost_calls = []

    def cost_callback(*a, **k):
        cost_calls.append((a, k))

    # Call the function under test
    result = await report_generation.write_conclusion(
        query=query,
        context=context,
        agent_role_prompt=agent_role_prompt,
        config=cfg,
        websocket=websocket,
        cost_callback=cost_callback,
        prompt_family=FakePromptFamily,
        extra_kw="extra_value",
    )

    # Verify return value
    assert result == "Generated conclusion"

    # Verify create_chat_completion was called and received expected keyword args
    assert "kwargs" in captured
    kw = captured["kwargs"]
    assert kw["model"] == cfg.smart_llm_model
    assert kw["temperature"] == 0.25
    assert kw["llm_provider"] == cfg.smart_llm_provider
    assert kw["stream"] is True
    assert kw["websocket"] is websocket
    assert kw["max_tokens"] == cfg.smart_token_limit
    assert kw["llm_kwargs"] == cfg.llm_kwargs
    assert kw["cost_callback"] is cost_callback
    assert kw["extra_kw"] == "extra_value"

    # Verify messages format and content
    messages = kw["messages"]
    assert isinstance(messages, list) and len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == agent_role_prompt
    assert messages[1]["role"] == "user"
    expected_user_content = FakePromptFamily.generate_report_conclusion(query=query, report_content=context, language=cfg.language)
    assert messages[1]["content"] == expected_user_content

    # Ensure cost_callback wasn't invoked by the fake LLM but remains callable
    assert callable(cost_callback)
    assert cost_calls == []


@pytest.mark.asyncio
async def test_write_conclusion_exception_logs_and_returns_empty(monkeypatch, caplog):
    # Import the module under test
    from gpt_researcher.actions import report_generation

    async def raising_create_chat_completion(*args, **kwargs):
        raise RuntimeError("boom")

    # Patch the create_chat_completion to raise
    monkeypatch.setattr(report_generation, "create_chat_completion", raising_create_chat_completion)

    # Use a simple PromptFamily
    class FakePromptFamily:
        @staticmethod
        def generate_report_conclusion(query: str, report_content: str, language: str):
            return "irrelevant"

    # Minimal config
    class DummyConfig:
        smart_llm_model = "m"
        smart_llm_provider = "p"
        language = "en"
        smart_token_limit = 1
        llm_kwargs = {}

    cfg = DummyConfig()

    # Capture error logs from the module's logger
    caplog.set_level(logging.ERROR, logger=report_generation.__name__)
    result = await report_generation.write_conclusion(
        query="q",
        context="c",
        agent_role_prompt="role",
        config=cfg,
        prompt_family=FakePromptFamily,
    )

    # On exception, function should return empty string
    assert result == ""

    # And an error should have been logged containing the exception message
    assert any("Error in writing conclusion" in rec.getMessage() and "boom" in rec.getMessage() for rec in caplog.records)
