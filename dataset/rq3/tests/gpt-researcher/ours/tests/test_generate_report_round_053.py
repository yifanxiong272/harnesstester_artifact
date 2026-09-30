import importlib
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest

MODULE = importlib.import_module("gpt_researcher.actions.report_generation")

@pytest.mark.asyncio
async def test_subtopic_no_images_round_053(monkeypatch):
    """
    Covers branch where report_type == 'subtopic_report' and available_images is empty.
    Ensures generate_prompt result is passed into create_chat_completion messages and the returned report is propagated.
    """
    # Arrange
    generated_text = "GEN_PROMPT_SUBTOPIC"

    # Stub get_prompt_by_report_type to return a callable that returns generated_text
    def fake_get_prompt_by_report_type(rt, pf):
        def inner(*args, **kwargs):
            return generated_text
        return inner

    # Async mock for create_chat_completion that returns a deterministic report
    create_mock = AsyncMock(return_value="REPORT1")

    monkeypatch.setattr(MODULE, "get_prompt_by_report_type", fake_get_prompt_by_report_type)
    monkeypatch.setattr(MODULE, "create_chat_completion", create_mock)

    cfg = SimpleNamespace(
        report_format="md",
        total_words=100,
        language="en",
        smart_llm_model="model-x",
        smart_llm_provider="prov",
        smart_token_limit=500,
        llm_kwargs={},
    )

    # Act
    result = await MODULE.generate_report(
        query="Q",
        context="CTX",
        agent_role_prompt="ROLE_PROMPT",
        report_type="subtopic_report",
        tone=None,
        report_source="source",
        websocket=None,
        cfg=cfg,
        main_topic="",
        existing_headers=[],
        relevant_written_contents=[],
        cost_callback=None,
        custom_prompt="",
    )

    # Assert
    assert result == "REPORT1"
    # create_chat_completion should have been awaited exactly once
    assert create_mock.await_count == 1
    # Inspect the messages passed to the LLM: user content should contain the generated prompt
    called_kwargs = create_mock.call_args[1]
    assert "messages" in called_kwargs
    messages = called_kwargs["messages"]
    # messages should include a system and a user message
    assert any(m.get("role") == "system" for m in messages)
    assert any(m.get("role") == "user" and generated_text in m.get("content", "") for m in messages)


@pytest.mark.asyncio
async def test_custom_prompt_with_images_round_053(monkeypatch):
    """
    Covers the custom_prompt branch and the available_images concatenation branch.
    Ensures the final content passed to create_chat_completion contains the custom prompt, context, and the AVAILABLE IMAGES block.
    """
    # Arrange
    create_mock = AsyncMock(return_value="REPORT2")
    monkeypatch.setattr(MODULE, "create_chat_completion", create_mock)

    cfg = SimpleNamespace(
        report_format="md",
        total_words=200,
        language="en",
        smart_llm_model="model-y",
        smart_llm_provider="prov-y",
        smart_token_limit=600,
        llm_kwargs={},
    )

    available_images = [
        {"url": "http://img.test/1.png", "title": "Title", "section_hint": "Intro"}
    ]

    # Act
    result = await MODULE.generate_report(
        query="Q2",
        context="CTX2",
        agent_role_prompt="ROLE_PROMPT_2",
        report_type="normal",
        tone=None,
        report_source="source2",
        websocket=None,
        cfg=cfg,
        main_topic="",
        existing_headers=[],
        relevant_written_contents=[],
        cost_callback=None,
        custom_prompt="MY_CUSTOM_PROMPT",
        available_images=available_images,
    )

    # Assert
    assert result == "REPORT2"
    assert create_mock.await_count == 1
    called_kwargs = create_mock.call_args[1]
    messages = called_kwargs["messages"]
    # For custom_prompt branch, the first user message content should start with the custom prompt and context
    user_msgs = [m for m in messages if m.get("role") == "user"]
    assert user_msgs, "expected a user message in messages"
    full_content = user_msgs[0]["content"]
    assert "MY_CUSTOM_PROMPT" in full_content
    assert "Context: CTX2" in full_content
    # The AVAILABLE IMAGES header and the specific image markdown line should be present
    assert "AVAILABLE IMAGES" in full_content
    assert "- Image 1: ![Title](http://img.test/1.png) - Intro" in full_content


@pytest.mark.asyncio
async def test_create_chat_completion_recover_round_053(monkeypatch):
    """
    Simulates create_chat_completion failing the first time (raising) and succeeding on the retry path in the outer except.
    Verifies the second call (the fallback) is used and contains a single user message that prepends agent_role_prompt.
    """
    # Prepare AsyncMock to raise on first await, return on second
    create_mock = AsyncMock(side_effect=[Exception("first-fail"), "RECOVERED_REPORT"])
    monkeypatch.setattr(MODULE, "create_chat_completion", create_mock)

    # Use a prompt provider stub (not used in this branch because custom_prompt empty and report_type not subtopic)
    def fake_get_prompt_by_report_type(rt, pf):
        return lambda *a, **k: "IGNORED"

    monkeypatch.setattr(MODULE, "get_prompt_by_report_type", fake_get_prompt_by_report_type)

    cfg = SimpleNamespace(
        report_format="md",
        total_words=50,
        language="en",
        smart_llm_model="model-z",
        smart_llm_provider="prov-z",
        smart_token_limit=300,
        llm_kwargs={},
    )

    result = await MODULE.generate_report(
        query="Q3",
        context="CTX3",
        agent_role_prompt="ROLE_PROMPT_3",
        report_type="normal",
        tone=None,
        report_source="source3",
        websocket=None,
        cfg=cfg,
        custom_prompt="",
    )

    # Assert fallback used and returned
    assert result == "RECOVERED_REPORT"
    # create_chat_completion should have been awaited twice
    assert create_mock.await_count == 2
    # Inspect the second call: it should only send a single user message that begins with the agent_role_prompt
    second_call_kwargs = create_mock.call_args_list[1][1]
    msgs = second_call_kwargs["messages"]
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"].startswith("ROLE_PROMPT_3\n\n")


@pytest.mark.asyncio
async def test_create_chat_completion_both_fail_round_053(monkeypatch, capsys):
    """
    Simulates both create_chat_completion attempts raising an Exception. Expects generate_report to catch and print the final error and return None.
    """
    create_mock = AsyncMock(side_effect=[Exception("err1"), Exception("err2")])
    monkeypatch.setattr(MODULE, "create_chat_completion", create_mock)

    # Minimal stub for prompt provider
    monkeypatch.setattr(MODULE, "get_prompt_by_report_type", lambda rt, pf: (lambda *a, **k: "X"))

    cfg = SimpleNamespace(
        report_format="md",
        total_words=10,
        language="en",
        smart_llm_model="m",
        smart_llm_provider="p",
        smart_token_limit=10,
        llm_kwargs={},
    )

    result = await MODULE.generate_report(
        query="Qfail",
        context="CTXfail",
        agent_role_prompt="ROLE_FAIL",
        report_type="normal",
        tone=None,
        report_source="rs",
        websocket=None,
        cfg=cfg,
        custom_prompt="",
    )

    # Should return None when both attempts fail
    assert result is None
    # Two attempts should have been made
    assert create_mock.await_count == 2

    # The function prints the final exception; capture and assert
    captured = capsys.readouterr()
    assert "Error in generate_report:" in captured.out
