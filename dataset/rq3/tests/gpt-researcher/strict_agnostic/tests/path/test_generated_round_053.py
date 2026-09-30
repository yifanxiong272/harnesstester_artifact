import asyncio
import pytest
from types import SimpleNamespace

import gpt_researcher.actions.report_generation as rg

# All tests end with _round_053 as required.

@pytest.mark.asyncio
async def test_subtopic_report_round_053(monkeypatch):
    """Covers branch where report_type == 'subtopic_report' (lines ~253-255).
    Asserts the prompt returned by get_prompt_by_report_type is forwarded as the user content
    and that the final report returned from the mocked LLM is propagated."""

    # Arrange: deterministic cfg and prompt generator
    cfg = SimpleNamespace(
        report_format="md",
        total_words=300,
        language="en",
        smart_llm_model="model-x",
        smart_llm_provider="prov",
        smart_token_limit=512,
        llm_kwargs={},
    )

    # Provide a generate_prompt that ignores inputs and returns a fixed string
    def fake_get_prompt_by_report_type(report_type, prompt_family):
        return lambda *args, **kwargs: "PROMPT_SUBTOPIC"

    monkeypatch.setattr(rg, "get_prompt_by_report_type", fake_get_prompt_by_report_type)

    calls = []

    async def fake_create_chat_completion(*args, **kwargs):
        # Record the kw used so we can assert on messages content
        calls.append({"args": args, "kwargs": kwargs})
        return "LLM_REPORT_SUBTOPIC"

    monkeypatch.setattr(rg, "create_chat_completion", fake_create_chat_completion)

    # Act
    result = await rg.generate_report(
        query="q",
        context="CTX",
        agent_role_prompt="ROLE",
        report_type="subtopic_report",
        tone=None,
        report_source="src",
        websocket=None,
        cfg=cfg,
        main_topic="main",
        existing_headers=[],
        relevant_written_contents=[],
        cost_callback=None,
        custom_prompt="",
        headers=None,
    )

    # Assert: final returned report and that user message content equals our prompt
    assert result == "LLM_REPORT_SUBTOPIC"
    assert calls, "create_chat_completion was not called"
    messages = calls[-1]["kwargs"]["messages"]
    # messages is a list of dicts; second one is the user content
    assert any(m.get("content") == "PROMPT_SUBTOPIC" for m in messages), "Expected generated prompt in messages"


@pytest.mark.asyncio
async def test_custom_prompt_round_053(monkeypatch):
    """Covers the custom_prompt branch (lines ~255-257).
    Asserts the custom prompt and context are combined and passed to the LLM."""

    cfg = SimpleNamespace(
        report_format="md",
        total_words=100,
        language="en",
        smart_llm_model="m",
        smart_llm_provider="p",
        smart_token_limit=100,
        llm_kwargs={},
    )

    # get_prompt_by_report_type should not be used in this branch, but provide a stub
    monkeypatch.setattr(rg, "get_prompt_by_report_type", lambda rt, pf: (lambda *a, **k: "UNUSED"))

    captured = {}

    async def fake_create_chat_completion(*args, **kwargs):
        captured["kwargs"] = kwargs
        return "LLM_REPORT_CUSTOM"

    monkeypatch.setattr(rg, "create_chat_completion", fake_create_chat_completion)

    custom = "MyCustomPrompt"
    ctx = "SOME CONTEXT"
    result = await rg.generate_report(
        query="ignored",
        context=ctx,
        agent_role_prompt="ROLEP",
        report_type="regular",
        tone=None,
        report_source="src",
        websocket=None,
        cfg=cfg,
        main_topic="",
        existing_headers=[],
        relevant_written_contents=[],
        cost_callback=None,
        custom_prompt=custom,
        headers=None,
    )

    assert result == "LLM_REPORT_CUSTOM"
    assert "kwargs" in captured
    messages = captured["kwargs"]["messages"]
    # The user message should contain the custom prompt and the context prefix
    expected_fragment = f"{custom}\n\nContext: {ctx}"
    assert any(expected_fragment in m.get("content", "") for m in messages), "Custom prompt + context not found in messages"


@pytest.mark.asyncio
async def test_available_images_round_053(monkeypatch):
    """Covers the available_images branch (lines ~261-274).
    Asserts that the formatted AVAILABLE IMAGES block is appended to the content passed to the LLM."""

    cfg = SimpleNamespace(
        report_format="md",
        total_words=200,
        language="en",
        smart_llm_model="mm",
        smart_llm_provider="pp",
        smart_token_limit=200,
        llm_kwargs={},
    )

    # A prompt generator used in the default (non-custom, non-subtopic) branch
    def fake_get_prompt_by_report_type(report_type, prompt_family):
        return lambda *args, **kwargs: "BASE_PROMPT"

    monkeypatch.setattr(rg, "get_prompt_by_report_type", fake_get_prompt_by_report_type)

    captured = {}

    async def fake_create_chat_completion(*args, **kwargs):
        captured["kwargs"] = kwargs
        return "LLM_REPORT_WITH_IMAGES"

    monkeypatch.setattr(rg, "create_chat_completion", fake_create_chat_completion)

    images = [{"url": "http://example.com/img.png", "title": "ImageTitle", "section_hint": "Intro"}]

    result = await rg.generate_report(
        query="q",
        context="CTX",
        agent_role_prompt="ROLE",
        report_type="regular",
        tone=None,
        report_source="src",
        websocket=None,
        cfg=cfg,
        main_topic="",
        existing_headers=[],
        relevant_written_contents=[],
        cost_callback=None,
        custom_prompt="",
        headers=None,
        available_images=images,
    )

    assert result == "LLM_REPORT_WITH_IMAGES"
    assert "kwargs" in captured
    messages = captured["kwargs"]["messages"]
    # The content should include the AVAILABLE IMAGES header and the formatted image line
    content = "".join(m.get("content", "") for m in messages)
    assert "AVAILABLE IMAGES:" in content
    assert "- Image 1: ![ImageTitle](http://example.com/img.png) - Intro" in content


@pytest.mark.asyncio
async def test_retry_on_exception_round_053(monkeypatch):
    """Covers exception -> retry success path (lines ~290-305).
    First create_chat_completion call raises, second call succeeds and uses agent_role_prompt + content layout."""

    cfg = SimpleNamespace(
        report_format="md",
        total_words=100,
        language="en",
        smart_llm_model="m1",
        smart_llm_provider="p1",
        smart_token_limit=100,
        llm_kwargs={},
    )

    monkeypatch.setattr(rg, "get_prompt_by_report_type", lambda rt, pf: (lambda *a, **k: "BASE"))

    state = {"calls": 0, "kwargs_first": None, "kwargs_second": None}

    async def flaky_create_chat_completion(*args, **kwargs):
        state["calls"] += 1
        if state["calls"] == 1:
            # simulate LLM failure on first attempt
            raise Exception("simulated LLM failure")
        else:
            # record the kwargs for the retry call
            state["kwargs_second"] = kwargs
            return "LLM_AFTER_RETRY"

    monkeypatch.setattr(rg, "create_chat_completion", flaky_create_chat_completion)

    agent_prompt = "AGENT_ROLE"

    result = await rg.generate_report(
        query="q",
        context="CTX",
        agent_role_prompt=agent_prompt,
        report_type="regular",
        tone=None,
        report_source="src",
        websocket=None,
        cfg=cfg,
        main_topic="",
        existing_headers=[],
        relevant_written_contents=[],
        cost_callback=None,
        custom_prompt="",
        headers=None,
    )

    # After the retry the returned value should be from the second successful call
    assert result == "LLM_AFTER_RETRY"
    assert state["calls"] >= 2
    # The retry invocation changes messages as per the except block: single user role with agent_role_prompt + content
    kwargs_retry = state["kwargs_second"]
    assert kwargs_retry is not None
    messages = kwargs_retry.get("messages", [])
    # Confirm that the agent_role_prompt is included in the single user message sent during retry
    assert any(agent_prompt in m.get("content", "") for m in messages), "Agent role prompt not forwarded in retry messages"


@pytest.mark.asyncio
async def test_both_calls_fail_round_053(monkeypatch):
    """Covers the case where both LLM attempts raise and generate_report returns the initial (empty) report (lines ~306-309).
    We assert that the function returns an empty string when both calls fail."""

    cfg = SimpleNamespace(
        report_format="md",
        total_words=50,
        language="en",
        smart_llm_model="m2",
        smart_llm_provider="p2",
        smart_token_limit=50,
        llm_kwargs={},
    )

    monkeypatch.setattr(rg, "get_prompt_by_report_type", lambda rt, pf: (lambda *a, **k: "BASE"))

    async def always_fail(*args, **kwargs):
        raise Exception("permanent failure")

    monkeypatch.setattr(rg, "create_chat_completion", always_fail)

    result = await rg.generate_report(
        query="q",
        context="CTX",
        agent_role_prompt="ROLE",
        report_type="regular",
        tone=None,
        report_source="src",
        websocket=None,
        cfg=cfg,
        main_topic="",
        existing_headers=[],
        relevant_written_contents=[],
        cost_callback=None,
        custom_prompt="",
        headers=None,
    )

    # Both calls failed and generate_report swallows the exception; final report should be the initialized value
    assert result == "" or result is None or result == None or result == ''
