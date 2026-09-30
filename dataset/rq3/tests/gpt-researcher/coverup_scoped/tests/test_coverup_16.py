# file: gpt_researcher/actions/report_generation.py:209-309
# asked: {"lines": [249, 250, 251, 253, 254, 255, 256, 258, 261, 262, 263, 264, 266, 271, 274, 275, 276, 277, 278, 279, 281, 282, 283, 284, 285, 286, 287, 288, 290, 291, 292, 293, 294, 295, 297, 298, 299, 300, 301, 302, 303, 304, 306, 307, 309], "branches": [[253, 254], [253, 255], [255, 256], [255, 258], [261, 262], [261, 274]]}
# gained: {"lines": [249, 250, 251, 253, 254, 255, 256, 258, 261, 262, 263, 264, 266, 271, 274, 275, 276, 277, 278, 279, 281, 282, 283, 284, 285, 286, 287, 288, 290, 291, 292, 293, 294, 295, 297, 298, 299, 300, 301, 302, 303, 304, 306, 307, 309], "branches": [[253, 254], [253, 255], [255, 256], [255, 258], [261, 262], [261, 274]]}

import importlib
from types import SimpleNamespace
import pytest


def load_report_module():
    """
    Try to import the report_generation module from potential package paths used in different setups.
    Returns the imported module.
    """
    candidates = [
        "gpt_researcher.actions.report_generation",
        "gpt_researcher.gpt_researcher.actions.report_generation",
    ]
    last_exc = None
    for name in candidates:
        try:
            return importlib.import_module(name)
        except Exception as e:
            last_exc = e
    raise last_exc


@pytest.mark.asyncio
async def test_generate_report_subtopic_with_images_success(monkeypatch):
    mod = load_report_module()
    generate_report = mod.generate_report
    Tone = getattr(mod, "Tone")

    # Prepare a fake cfg
    cfg = SimpleNamespace(
        smart_llm_model="model-x",
        smart_llm_provider="prov",
        report_format="markdown",
        total_words=200,
        language="en",
        smart_token_limit=1500,
        llm_kwargs={"foo": "bar"},
    )

    # Fake generate_prompt which should be returned by get_prompt_by_report_type
    def fake_generate_prompt(*args, **kwargs):
        # Verify that called as expected for subtopic_report branch:
        # args: query, existing_headers, relevant_written_contents, main_topic, context
        assert len(args) >= 5
        return "GENERATED_PROMPT_SUBTOPIC"

    # Patch get_prompt_by_report_type in the module to return the fake_generate_prompt
    monkeypatch.setattr(mod, "get_prompt_by_report_type", lambda report_type, prompt_family: fake_generate_prompt)

    # Prepare available images
    available_images = [
        {"title": "Img A", "url": "http://a", "section_hint": "Intro"},
        {"alt_text": "Alt B", "url": "http://b"},
    ]

    # Capture the messages passed to create_chat_completion
    captured = {}

    async def fake_create_chat_completion(**kwargs):
        # Save for assertions
        captured.update(kwargs)
        # Return a fake report string
        return "REPORT_FROM_LLM_SUBTOPIC"

    # Patch the create_chat_completion used inside generate_report
    monkeypatch.setattr(mod, "create_chat_completion", fake_create_chat_completion)

    result = await generate_report(
        query="q1",
        context="CTX",
        agent_role_prompt="You are an agent.",
        report_type="subtopic_report",
        tone=getattr(Tone, "NEUTRAL", list(Tone)[0]),
        report_source="source",
        websocket=None,
        cfg=cfg,
        main_topic="Main",
        existing_headers=["h1"],
        relevant_written_contents=["c1"],
        cost_callback=None,
        custom_prompt="",
        headers=None,
        prompt_family=None,
        available_images=available_images,
    )

    # Assertions
    assert result == "REPORT_FROM_LLM_SUBTOPIC"
    # Ensure create_chat_completion was called and messages constructed properly
    assert "messages" in captured
    msgs = captured["messages"]
    # First message should be system role with agent_role_prompt
    assert any(m.get("role") == "system" and "You are an agent." in m.get("content", "") for m in msgs)
    # There should be a user message containing the generated prompt and the AVAILABLE IMAGES block
    user_msgs = [m for m in msgs if m["role"] == "user"]
    assert len(user_msgs) == 1
    user_content = user_msgs[0]["content"]
    assert "GENERATED_PROMPT_SUBTOPIC" in user_content
    assert "AVAILABLE IMAGES" in user_content
    # Images info should include both images and correct markdown
    assert "- Image 1: ![Img A](http://a) - Intro" in user_content
    assert "- Image 2: ![Alt B](http://b) - General" in user_content
    # Ensure other kwargs passed are as expected
    assert captured.get("model") == cfg.smart_llm_model
    assert captured.get("temperature") == 0.35
    assert captured.get("stream") is True
    assert captured.get("websocket") is None
    assert captured.get("max_tokens") == cfg.smart_token_limit


@pytest.mark.asyncio
async def test_generate_report_custom_prompt_first_try_fails_then_second_succeeds(monkeypatch):
    mod = load_report_module()
    generate_report = mod.generate_report
    Tone = getattr(mod, "Tone")

    cfg = SimpleNamespace(
        smart_llm_model="m2",
        smart_llm_provider="prov2",
        report_format="html",
        total_words=300,
        language="fr",
        smart_token_limit=2000,
        llm_kwargs={},
    )

    # For non-subtopic and custom_prompt set, get_prompt_by_report_type should not be used,
    # but patch it defensively to raise if called unexpectedly
    def should_not_be_called(*args, **kwargs):
        raise AssertionError("generate_prompt was called unexpectedly")

    monkeypatch.setattr(mod, "get_prompt_by_report_type", lambda report_type, prompt_family: should_not_be_called)

    # Create a sequence of behaviors: first call raises, second returns a value.
    call_log = {"calls": []}

    async def create_chat_completion_sequenced(**kwargs):
        call_log["calls"].append(kwargs)
        if len(call_log["calls"]) == 1:
            raise RuntimeError("simulated LLM outage")
        return "REPORT_SECOND_TRY"

    monkeypatch.setattr(mod, "create_chat_completion", create_chat_completion_sequenced)

    # Run generate_report with custom_prompt branch
    result = await generate_report(
        query="irrelevant",
        context="CONTEXT_DATA",
        agent_role_prompt="RolePromptHere",
        report_type="some_other_report",
        tone=getattr(Tone, "NEUTRAL", list(Tone)[0]),
        report_source="rsrc",
        websocket=None,
        cfg=cfg,
        custom_prompt="My custom prompt",
    )

    # Should succeed with second call's return value
    assert result == "REPORT_SECOND_TRY"
    # Two calls to create_chat_completion should have been made
    assert len(call_log["calls"]) == 2

    # Inspect the first call: should be the try block signature (system + user)
    first_msgs = call_log["calls"][0]["messages"]
    assert any(m.get("role") == "system" and "RolePromptHere" in m.get("content", "") for m in first_msgs)
    assert any(m.get("role") == "user" and "My custom prompt" in m.get("content", "") for m in first_msgs)

    # Inspect the second call: should be only a single user message combining agent prompt and content
    second_msgs = call_log["calls"][1]["messages"]
    assert len(second_msgs) == 1
    assert second_msgs[0]["role"] == "user"
    assert "RolePromptHere" in second_msgs[0]["content"]
    assert "My custom prompt" in second_msgs[0]["content"]
    assert "Context: CONTEXT_DATA" in second_msgs[0]["content"]


@pytest.mark.asyncio
async def test_generate_report_both_tries_fail_prints_error_and_returns_empty(monkeypatch, capsys):
    mod = load_report_module()
    generate_report = mod.generate_report
    Tone = getattr(mod, "Tone")

    cfg = SimpleNamespace(
        smart_llm_model="m3",
        smart_llm_provider="prov3",
        report_format="txt",
        total_words=50,
        language="de",
        smart_token_limit=500,
        llm_kwargs={},
    )

    # Patch get_prompt_by_report_type to a simple function that returns something
    monkeypatch.setattr(mod, "get_prompt_by_report_type", lambda report_type, prompt_family: (lambda *a, **k: "PROMPT_THAT_WOULD_BE_USED"))

    async def always_raise(**kwargs):
        raise RuntimeError("permanent failure")

    monkeypatch.setattr(mod, "create_chat_completion", always_raise)

    result = await generate_report(
        query="q_fail",
        context="ctx_fail",
        agent_role_prompt="agent_fail",
        report_type="regular_report",
        tone=getattr(Tone, "NEUTRAL", list(Tone)[0]),
        report_source="src_fail",
        websocket=None,
        cfg=cfg,
    )

    # When both attempts fail, generate_report should return an empty string
    assert result == ""
    # And an error should have been printed
    captured = capsys.readouterr()
    assert "Error in generate_report" in captured.out
