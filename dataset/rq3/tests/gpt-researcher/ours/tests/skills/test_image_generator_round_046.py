import pytest
import json
from types import SimpleNamespace
from gpt_researcher.skills import image_generator as ig

# Helper to bind the async method to a lightweight fake instance
class DummyGenerator:
    def __init__(self, max_images=2):
        # minimal cfg and researcher shapes expected by the method
        self.cfg = SimpleNamespace(
            fast_llm_model="fast-model",
            fast_llm_provider="provider",
            llm_kwargs={},
        )
        self.researcher = SimpleNamespace(add_costs=lambda *a, **k: None)
        self.max_images = max_images


@pytest.mark.asyncio
async def test_valid_response_without_codeblock_round_046(monkeypatch):
    """Return a clean JSON array string and ensure valid concepts are returned and limited by max_images."""
    dummy = DummyGenerator(max_images=2)

    # prepare a response with two valid concepts and one extra
    concepts = [
        {"title": "A", "prompt": "Prompt A is sufficiently long and descriptive...", "section_hint": "Intro"},
        {"title": "B", "prompt": "Prompt B details the diagram layout...", "section_hint": "Methods"},
        {"title": "C", "prompt": "Prompt C...", "section_hint": "Results"},
    ]
    response_text = json.dumps(concepts)

    async def fake_create_chat_completion(*args, **kwargs):
        return response_text

    monkeypatch.setattr(ig, "create_chat_completion", fake_create_chat_completion)

    # Bind and call the async method
    method = ig.ImageGenerator._plan_image_concepts.__get__(dummy, ig.ImageGenerator)
    result = await method("short context", "some query")

    # Expect exactly the first two concepts (max_images=2)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["title"] == "A"
    assert result[1]["title"] == "B"


@pytest.mark.asyncio
async def test_response_with_codeblock_and_truncation_round_046(monkeypatch):
    """Response wrapped in a fenced code block should be unwrapped; context longer than max should be truncated in the prompt sent to LLM."""
    # create a very long context to trigger truncation ( > 6000 chars )
    long_context = "x" * 7000
    dummy = DummyGenerator(max_images=10)

    # Prepare JSON wrapped in a codeblock as might be returned by an LLM
    concepts = [
        {"title": "Sys Arch", "prompt": "Detailed layout of components...", "section_hint": "Architecture"},
        {"title": "Comparison", "prompt": "Side-by-side comparison chart...", "section_hint": "Results"},
    ]
    inner_json = json.dumps(concepts)
    fenced = "```json\n" + inner_json + "\n```"

    captured_messages = {}

    async def fake_create_chat_completion(model, messages, temperature, llm_provider, max_tokens, llm_kwargs, cost_callback):
        # capture the messages passed to ensure truncation was applied
        captured_messages['messages'] = messages
        return fenced

    monkeypatch.setattr(ig, "create_chat_completion", fake_create_chat_completion)

    method = ig.ImageGenerator._plan_image_concepts.__get__(dummy, ig.ImageGenerator)
    result = await method(long_context, "query for diagrams")

    # It should parse out the fenced JSON and return the two concepts
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["title"] == "Sys Arch"

    # Ensure the planning prompt included a truncated context (6000 x's) and not the full 7000
    messages = captured_messages.get('messages')
    assert messages is not None and isinstance(messages, list)
    # user message is second element per implementation
    user_msg = messages[1]["content"]
    assert "x" * 6000 in user_msg
    assert "x" * 7000 not in user_msg


@pytest.mark.asyncio
async def test_json_decode_error_round_046(monkeypatch):
    """If the LLM returns text that isn't valid JSON, method should catch JSONDecodeError and return an empty list."""
    dummy = DummyGenerator(max_images=3)

    async def fake_create_chat_completion(*args, **kwargs):
        return "this is not json"

    monkeypatch.setattr(ig, "create_chat_completion", fake_create_chat_completion)

    method = ig.ImageGenerator._plan_image_concepts.__get__(dummy, ig.ImageGenerator)
    result = await method("ctx", "q")

    assert result == []


@pytest.mark.asyncio
async def test_create_chat_completion_exception_round_046(monkeypatch):
    """If create_chat_completion raises a general Exception, method should catch it and return an empty list."""
    dummy = DummyGenerator()

    async def fake_create_chat_completion(*args, **kwargs):
        raise RuntimeError("some LLM error")

    monkeypatch.setattr(ig, "create_chat_completion", fake_create_chat_completion)

    method = ig.ImageGenerator._plan_image_concepts.__get__(dummy, ig.ImageGenerator)
    result = await method("ctx", "q")

    assert result == []
