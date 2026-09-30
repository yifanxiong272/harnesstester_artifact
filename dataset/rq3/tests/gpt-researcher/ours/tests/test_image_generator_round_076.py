import asyncio
from types import SimpleNamespace
import pytest

from gpt_researcher.skills import image_generator
from gpt_researcher.skills.image_generator import ImageGenerator

# All tests deterministic and avoid any network or real-provider calls by
# patching the create_chat_completion symbol on the module under test and
# by constructing ImageGenerator instances via __new__ to avoid calling its
# real __init__.

@pytest.mark.asyncio
async def test_analyze_report_is_disabled_round_076(monkeypatch):
    # Arrange: create instance without running __init__, make is_enabled False
    inst = ImageGenerator.__new__(ImageGenerator)
    inst.is_enabled = lambda: False

    # To be extra safe, ensure create_chat_completion would fail if called
    async def _fail_if_called(*args, **kwargs):
        raise AssertionError("create_chat_completion should not be called when disabled")

    monkeypatch.setattr(image_generator, "create_chat_completion", _fail_if_called)

    # Act
    result = await inst.analyze_report_for_images("some report text", "query")

    # Assert
    assert result == [], "When disabled, analyze_report_for_images must return an empty list"


@pytest.mark.asyncio
async def test_analyze_report_no_sections_round_076(monkeypatch):
    # Arrange: enabled but _extract_sections returns empty -> should log warning and return []
    inst = ImageGenerator.__new__(ImageGenerator)
    inst.is_enabled = lambda: True
    inst._extract_sections = lambda report: []

    # Ensure create_chat_completion is not invoked
    async def _fail_if_called(*args, **kwargs):
        raise AssertionError("create_chat_completion should not be called when no sections")

    monkeypatch.setattr(image_generator, "create_chat_completion", _fail_if_called)

    # Act
    result = await inst.analyze_report_for_images("report with nothing relevant", "query")

    # Assert
    assert result == [], "When no sections are found, analyze_report_for_images must return an empty list"


@pytest.mark.asyncio
async def test_analyze_report_success_limits_max_images_round_076(monkeypatch):
    # Arrange: enabled, sections present, create_chat_completion returns a stubbed response,
    # and _parse_analysis_response returns more suggestions than max_images to test trimming.
    inst = ImageGenerator.__new__(ImageGenerator)
    inst.is_enabled = lambda: True
    inst._extract_sections = lambda report: ["s1", "s2", "s3"]
    inst._build_analysis_prompt = lambda query, sections: f"PROMPT for {query} on {len(sections)} sections"

    # create a cfg with the attributes the code passes to create_chat_completion
    inst.cfg = SimpleNamespace(
        fast_llm_model="fast-model-x",
        fast_llm_provider="prov-x",
        llm_kwargs={"k": "v"},
    )

    # Force max_images to a trimmed value
    inst.max_images = 2

    # record the kwargs passed to the mocked create_chat_completion for assertions
    seen = {}

    async def fake_create_chat_completion(*args, **kwargs):
        # record some expected keys to ensure call shape
        seen.update({"model": kwargs.get("model"), "llm_provider": kwargs.get("llm_provider"), "messages": kwargs.get("messages")})
        # return an opaque object; _parse_analysis_response does not depend on exact chat shape here
        return {"ok": True}

    monkeypatch.setattr(image_generator, "create_chat_completion", fake_create_chat_completion)

    # _parse_analysis_response should accept the response and sections and return a list of suggestions
    suggestions = [
        {"section": "s1", "prompt": "p1"},
        {"section": "s2", "prompt": "p2"},
        {"section": "s3", "prompt": "p3"},
    ]
    inst._parse_analysis_response = lambda response, sections: suggestions

    # Act
    result = await inst.analyze_report_for_images("full report text", "important query")

    # Assert: ensure returned list is trimmed to inst.max_images and in original order
    assert isinstance(result, list)
    assert len(result) == 2
    assert result == suggestions[:2]
    # Ensure create_chat_completion was called with the cfg values supplied
    assert seen.get("model") == "fast-model-x"
    assert seen.get("llm_provider") == "prov-x"
    # messages should be a list with two dicts (system + user) as constructed by the code
    msgs = seen.get("messages")
    assert isinstance(msgs, list) and len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"


@pytest.mark.asyncio
async def test_analyze_report_handles_llm_exception_round_076(monkeypatch):
    # Arrange: enabled and sections present, but create_chat_completion raises -> should return []
    inst = ImageGenerator.__new__(ImageGenerator)
    inst.is_enabled = lambda: True
    inst._extract_sections = lambda report: ["s1"]
    inst._build_analysis_prompt = lambda query, sections: "prompt"
    inst.cfg = SimpleNamespace(
        fast_llm_model="m",
        fast_llm_provider="p",
        llm_kwargs={},
    )
    inst.max_images = 5

    async def raising_create_chat_completion(*args, **kwargs):
        raise RuntimeError("simulated llm failure")

    monkeypatch.setattr(image_generator, "create_chat_completion", raising_create_chat_completion)

    # Act
    result = await inst.analyze_report_for_images("report", "q")

    # Assert
    assert result == [], "If the LLM call raises, analyze_report_for_images must return an empty list"
