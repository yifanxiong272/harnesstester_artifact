import asyncio
import types
from types import SimpleNamespace
import pytest

# Import the module under test
from gpt_researcher.skills import image_generator as img_mod

# Access the async function object to call it with a fake self
_plan_image_concepts = img_mod.ImageGenerator._plan_image_concepts


def make_fake_self(max_images=2):
    class Cfg:
        fast_llm_model = "fast-model"
        fast_llm_provider = "prov"
        llm_kwargs = {"foo": "bar"}

    class Researcher:
        def add_costs(self, *a, **k):
            # deterministic no-op cost recorder
            return None

    return SimpleNamespace(cfg=Cfg(), researcher=Researcher(), max_images=max_images)


def run_coro(coro):
    # Create and use a fresh event loop to avoid warnings about missing current loop
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_plan_image_concepts_truncate_and_codeblock_removal_round_046(monkeypatch):
    """
    Exercise branch where context is truncated and the LLM response is wrapped in a ```json code block.
    Asserts:
    - The returned list is limited to max_images
    - Only valid dict concepts with 'title' and 'prompt' are kept
    - The planning prompt passed to the LLM contains the truncated context (<=6000 chars) and does NOT contain the full original long context
    """
    recorded = {}

    # Create a long context to trigger truncation path (max_context_length = 6000 in source)
    long_context = "X" * 7000

    # Return JSON wrapped in a code block; include 3 items but one is invalid to test filtering
    response_string = (
        "```json\n"
        "[\n"
        "  {\"title\": \"T1\", \"prompt\": \"This is prompt one with enough descriptive text to be realistic and verbose.\", \"section_hint\": \"S1\"},\n"
        "  {\"title\": \"T2\", \"prompt\": \"This is prompt two with additional descriptive text to simulate a detailed image request.\", \"section_hint\": \"S2\"},\n"
        "  {\"bad\": \"entry\"}\n"
        "]\n```")

    async def fake_create_chat_completion(*, model=None, messages=None, temperature=None, llm_provider=None, max_tokens=None, llm_kwargs=None, cost_callback=None, **kwargs):
        # record the messages that were passed in for assertions
        recorded['messages'] = messages
        # return the prepared code-block-wrapped JSON
        return response_string

    # Monkeypatch the create_chat_completion in the module
    monkeypatch.setattr(img_mod, "create_chat_completion", fake_create_chat_completion)

    fake_self = make_fake_self(max_images=2)

    result = run_coro(_plan_image_concepts(fake_self, long_context, "some query"))

    # Should filter out the invalid entry and limit to max_images
    assert isinstance(result, list)
    assert len(result) == 2
    for item in result:
        assert isinstance(item, dict)
        assert 'title' in item and 'prompt' in item

    # Inspect the planning prompt that was constructed and passed to create_chat_completion
    assert 'messages' in recorded
    planning_content = recorded['messages'][1]['content']
    assert 'RESEARCH CONTEXT:' in planning_content

    # The truncated context should appear, and the full long context should NOT appear
    truncated = "X" * 6000
    full = "X" * 7000
    assert truncated in planning_content
    assert full not in planning_content


def test_plan_image_concepts_invalid_json_round_046(monkeypatch):
    """
    Exercise the JSON decoding error branch by returning plain invalid JSON (no code fences).
    Asserts:
    - The function returns an empty list on json.JSONDecodeError
    """
    async def fake_create_chat_completion(*, model=None, messages=None, temperature=None, llm_provider=None, max_tokens=None, llm_kwargs=None, cost_callback=None, **kwargs):
        # Return a non-JSON string (no code fences) to trigger JSONDecodeError after strip
        return "this is not json"

    monkeypatch.setattr(img_mod, "create_chat_completion", fake_create_chat_completion)

    fake_self = make_fake_self(max_images=3)

    result = run_coro(_plan_image_concepts(fake_self, "short context", "q"))

    assert result == []


def test_plan_image_concepts_create_chat_exception_round_046(monkeypatch):
    """
    Exercise the general exception handling branch by making create_chat_completion raise.
    Asserts:
    - The function returns an empty list when the underlying LLM call raises an exception
    """
    async def fake_create_chat_completion(*, model=None, messages=None, temperature=None, llm_provider=None, max_tokens=None, llm_kwargs=None, cost_callback=None, **kwargs):
        raise RuntimeError("simulated LLM failure")

    monkeypatch.setattr(img_mod, "create_chat_completion", fake_create_chat_completion)

    fake_self = make_fake_self()

    result = run_coro(_plan_image_concepts(fake_self, "ctx", "q"))

    assert result == []
