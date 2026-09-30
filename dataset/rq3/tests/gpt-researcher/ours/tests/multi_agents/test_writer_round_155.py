import pytest

import multi_agents.agents.writer as writer_mod
from multi_agents.agents.writer import WriterAgent


@pytest.mark.asyncio
async def test_write_sections_includes_guidelines_and_returns_response_round_155(monkeypatch):
    """
    Exercise the path where task.follow_guidelines is True so the user prompt includes the
    guidelines text. Also assert the function forwards the model and response_format and
    returns exactly what the model call returned.
    """

    captured = {}

    async def fake_call_model(prompt, model, response_format="json"):
        # capture the prompt and other args for assertions
        captured['prompt'] = prompt
        captured['model'] = model
        captured['response_format'] = response_format
        # return a deterministic JSON-like object the code should return unchanged
        return {"intro": "Intro text.", "conclusion": "Conclusion text."}

    # Patch the call_model symbol where WriterAgent resolves it
    monkeypatch.setattr(writer_mod, "call_model", fake_call_model)

    agent = WriterAgent(websocket=None, stream_output=False, headers={})

    research_state = {
        "title": "Test Topic",
        "research_data": {"finding": 42},
        "task": {
            "follow_guidelines": True,
            "guidelines": "Be concise and cite sources",
            "model": "test-model-v1",
        },
    }

    result = await agent.write_sections(research_state)

    # The mock returns this exact dict; write_sections should return it unchanged
    assert result == {"intro": "Intro text.", "conclusion": "Conclusion text."}

    # Validate call_model was invoked with the expected model and json response format
    assert captured["model"] == "test-model-v1"
    assert captured["response_format"] == "json"

    # Validate the prompt structure: list with system and user messages
    prompt = captured.get("prompt")
    assert isinstance(prompt, list) and len(prompt) >= 2
    assert prompt[0]["role"] == "system"
    assert prompt[1]["role"] == "user"

    # The user content should include the query, research data and the guidelines text
    user_content = prompt[1]["content"]
    assert "Query or Topic: Test Topic" in user_content
    assert "Research data: {'finding': 42}" in user_content or "Research data: {\"finding\": 42}" in user_content
    assert "You must follow the guidelines provided: Be concise and cite sources" in user_content


@pytest.mark.asyncio
async def test_write_sections_omits_guidelines_when_flag_false_round_155(monkeypatch):
    """
    Exercise the path where task.follow_guidelines is False so the user prompt does NOT include
    the guidelines text. Ensure the response is returned unchanged as well.
    """

    captured = {}

    async def fake_call_model(prompt, model, response_format="json"):
        captured['prompt'] = prompt
        captured['model'] = model
        captured['response_format'] = response_format
        return {"intro": "X", "conclusion": "Y"}

    monkeypatch.setattr(writer_mod, "call_model", fake_call_model)

    agent = WriterAgent(websocket=None, stream_output=False, headers={})

    research_state = {
        "title": "Another Topic",
        "research_data": [1, 2, 3],
        "task": {
            "follow_guidelines": False,
            "guidelines": "This should be ignored",
            "model": "another-model",
        },
    }

    result = await agent.write_sections(research_state)

    assert result == {"intro": "X", "conclusion": "Y"}

    prompt = captured.get("prompt")
    assert isinstance(prompt, list) and len(prompt) >= 2
    user_content = prompt[1]["content"]

    # Ensure guidelines text is not present when follow_guidelines is False
    assert "You must follow the guidelines provided:" not in user_content
    # Still contains the query and research data
    assert "Query or Topic: Another Topic" in user_content
    assert "Research data:" in user_content
