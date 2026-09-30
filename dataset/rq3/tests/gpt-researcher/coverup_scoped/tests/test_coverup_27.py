# file: gpt_researcher/skills/image_generator.py:182-269
# asked: {"lines": [197, 198, 200, 202, 205, 232, 233, 234, 235, 236, 237, 239, 240, 241, 242, 243, 247, 249, 250, 251, 253, 256, 257, 258, 259, 261, 262, 264, 265, 266, 267, 268, 269], "branches": [[249, 250], [249, 253], [257, 258], [257, 261], [258, 257], [258, 259]]}
# gained: {"lines": [197, 198, 200, 202, 205, 232, 233, 234, 235, 236, 237, 239, 240, 241, 242, 243, 247, 249, 250, 251, 253, 256, 257, 258, 259, 261, 262, 264, 265, 266, 267, 268, 269], "branches": [[249, 250], [249, 253], [257, 258], [257, 261], [258, 257], [258, 259]]}

import json
import importlib
from types import SimpleNamespace

import pytest

# Try both possible module import paths to be robust to package layout
try:
    image_generator_module = importlib.import_module("gpt_researcher.gpt_researcher.skills.image_generator")
except Exception:
    image_generator_module = importlib.import_module("gpt_researcher.skills.image_generator")

ImageGenerator = image_generator_module.ImageGenerator


@pytest.mark.asyncio
async def test_plan_image_concepts_success_with_truncation_and_codeblock(monkeypatch):
    # Create instance without running __init__
    ig = object.__new__(ImageGenerator)
    ig.cfg = SimpleNamespace(
        fast_llm_model="fast-model",
        fast_llm_provider="provider-x",
        llm_kwargs={"foo": "bar"},
    )
    ig.researcher = SimpleNamespace(add_costs=lambda *a, **k: None)
    ig.max_images = 3

    long_context = "X" * 7000
    query = "Which visuals clarify the study?"

    response_json = [
        {
            "title": "System Architecture",
            "prompt": "A layered architecture diagram showing frontend, API gateway, and microservices with clear arrows and labels, minimalistic color palette, and modern fonts for readability.",
            "section_hint": "Architecture",
        },
        {
            "title": "Comparison Chart",
            "prompt": "A side-by-side comparison infographic contrasting Method A and Method B, include pros/cons bullets, icons for each metric, and a highlighted summary box.",
            "section_hint": "Results",
        },
        {"not_title": "invalid-entry"},
    ]
    # Use unicode escapes for backticks to avoid any tooling that may mis-handle literal backticks.
    response_str = "\u0060\u0060\u0060json\n" + json.dumps(response_json) + "\n\u0060\u0060\u0060"

    captured = {}

    async def fake_create_chat_completion(**kwargs):
        captured.update(kwargs)
        return response_str

    monkeypatch.setattr(image_generator_module, "create_chat_completion", fake_create_chat_completion)

    result = await ig._plan_image_concepts(long_context, query)

    assert isinstance(result, list)
    # Third entry is invalid and should be filtered out
    assert len(result) == 2
    assert result[0]["title"] == "System Architecture"
    assert "architecture" in result[0]["prompt"].lower()
    assert result[1]["title"] == "Comparison Chart"

    # Validate the create_chat_completion call parameters were passed through
    assert captured.get("model") == ig.cfg.fast_llm_model
    assert isinstance(captured.get("messages"), list)
    user_messages = [m for m in captured["messages"] if m.get("role") == "user"]
    assert user_messages, "No user message sent to LLM"
    assert "RESEARCH QUERY: Which visuals clarify the study?" in user_messages[0]["content"]


@pytest.mark.asyncio
async def test_plan_image_concepts_handles_json_decode_error(monkeypatch):
    ig = object.__new__(ImageGenerator)
    ig.cfg = SimpleNamespace(
        fast_llm_model="fast-model",
        fast_llm_provider="provider-x",
        llm_kwargs={},
    )
    ig.researcher = SimpleNamespace(add_costs=lambda *a, **k: None)
    ig.max_images = 2

    async def fake_bad_json(**kwargs):
        # Return a string that is not valid JSON to provoke JSONDecodeError
        return "not a json array"

    monkeypatch.setattr(image_generator_module, "create_chat_completion", fake_bad_json)

    result = await ig._plan_image_concepts("short context", "sample query")
    assert result == []


@pytest.mark.asyncio
async def test_plan_image_concepts_handles_llm_exception(monkeypatch):
    ig = object.__new__(ImageGenerator)
    ig.cfg = SimpleNamespace(
        fast_llm_model="fast-model",
        fast_llm_provider="provider-x",
        llm_kwargs={},
    )
    ig.researcher = SimpleNamespace(add_costs=lambda *a, **k: None)
    ig.max_images = 2

    async def fake_raise(**kwargs):
        raise RuntimeError("LLM backend failure")

    monkeypatch.setattr(image_generator_module, "create_chat_completion", fake_raise)

    result = await ig._plan_image_concepts("context", "query")
    assert result == []
