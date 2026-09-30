# file: gpt_researcher/skills/image_generator.py:77-180
# asked: {"lines": [97, 98, 99, 101, 102, 103, 104, 105, 106, 110, 112, 113, 114, 116, 117, 118, 119, 120, 121, 125, 127, 129, 130, 131, 132, 133, 134, 135, 138, 139, 140, 141, 142, 143, 146, 147, 148, 149, 150, 152, 153, 154, 157, 158, 161, 162, 164, 165, 166, 167, 168, 169, 170, 173, 174, 175, 176, 177, 180], "branches": [[97, 98], [97, 101], [101, 102], [101, 110], [112, 113], [112, 116], [116, 117], [116, 125], [130, 131], [130, 138], [146, 147], [146, 154], [164, 165], [164, 180], [165, 166], [165, 173]]}
# gained: {"lines": [97, 98, 99, 101, 102, 103, 104, 105, 106, 110, 112, 113, 114, 116, 117, 118, 119, 120, 121, 125, 127, 129, 130, 131, 132, 133, 134, 135, 138, 139, 140, 141, 142, 143, 146, 147, 148, 149, 150, 152, 153, 154, 157, 158, 161, 162, 164, 165, 166, 167, 168, 169, 170, 173, 174, 175, 176, 177, 180], "branches": [[97, 98], [97, 101], [101, 102], [112, 113], [112, 116], [116, 117], [130, 131], [146, 147], [164, 165], [165, 166], [165, 173]]}

import pytest
from types import SimpleNamespace
import asyncio

from gpt_researcher.skills.image_generator import ImageGenerator


@pytest.mark.asyncio
async def test_plan_and_generate_images_disabled(monkeypatch):
    # Prevent any provider initialization side-effects
    monkeypatch.setattr(ImageGenerator, "_init_provider", lambda self: None)

    # Prepare researcher and generator
    researcher = SimpleNamespace(cfg=SimpleNamespace(image_generation_max_images=3), verbose=False, websocket=None)
    gen = ImageGenerator(researcher)

    # Force disabled
    monkeypatch.setattr(gen, "is_enabled", lambda: False)

    # Capture stream_output calls if any
    calls = []

    async def fake_stream_output(channel, event, message, websocket):
        calls.append((channel, event, message))

    # Patch module-level stream_output used in the method
    module_path = ImageGenerator.__module__
    monkeypatch.setattr(f"{module_path}.stream_output", fake_stream_output)

    result = await gen.plan_and_generate_images("some context", "some query")
    assert result == []
    # When disabled, no stream_output should be called
    assert calls == []


@pytest.mark.asyncio
async def test_plan_and_generate_images_no_concepts_verbose(monkeypatch):
    # Prevent provider init side-effects
    monkeypatch.setattr(ImageGenerator, "_init_provider", lambda self: None)

    # Set up researcher with verbose True
    researcher = SimpleNamespace(cfg=SimpleNamespace(image_generation_max_images=3), verbose=True, websocket=None)
    gen = ImageGenerator(researcher)

    # Enable generator
    monkeypatch.setattr(gen, "is_enabled", lambda: True)

    # _plan_image_concepts returns empty list -> early return
    async def fake_plan(context, query):
        return []
    monkeypatch.setattr(gen, "_plan_image_concepts", fake_plan)

    calls = []

    async def fake_stream_output(channel, event, message, websocket):
        calls.append((channel, event, message))

    module_path = ImageGenerator.__module__
    monkeypatch.setattr(f"{module_path}.stream_output", fake_stream_output)

    result = await gen.plan_and_generate_images("ctx", "query")
    assert result == []
    # Should have called the initial analyzing stream_output once
    assert any("Analyzing research context" in msg or "Analyzing" in msg for _, _, msg in calls)


@pytest.mark.asyncio
async def test_plan_and_generate_images_partial_success(monkeypatch):
    # Prevent provider init side-effects
    monkeypatch.setattr(ImageGenerator, "_init_provider", lambda self: None)

    researcher = SimpleNamespace(
        cfg=SimpleNamespace(image_generation_max_images=3, image_generation_style="sepia"),
        verbose=True,
        websocket=None,
    )
    gen = ImageGenerator(researcher)

    monkeypatch.setattr(gen, "is_enabled", lambda: True)

    # Two concepts: one will succeed, one will fail
    concepts = [
        {"title": "Sunset Diagram", "prompt": "a beautiful sunset over hills", "section_hint": "Introduction"},
        {"title": "Broken Scene", "prompt": "cause_error_generation", "section_hint": "Methods"},
    ]

    async def fake_plan(context, query):
        return concepts
    monkeypatch.setattr(gen, "_plan_image_concepts", fake_plan)

    # Fake image provider
    class FakeProvider:
        async def generate_image(self, prompt, context="", research_id="", num_images=1, style=None):
            if "cause_error" in prompt:
                raise RuntimeError("simulated provider failure")
            return [{"url": f"https://img.example/{prompt.replace(' ', '_')}.png", "id": 42}]

    gen.image_provider = FakeProvider()

    calls = []

    async def fake_stream_output(channel, event, message, websocket):
        calls.append((channel, event, message))

    module_path = ImageGenerator.__module__
    monkeypatch.setattr(f"{module_path}.stream_output", fake_stream_output)

    result = await gen.plan_and_generate_images("ctx", "query", research_id="rid123")
    # Only the first concept should have produced an image
    assert isinstance(result, list)
    assert len(result) == 1
    img = result[0]
    assert img["url"].startswith("https://img.example/")
    assert img["title"] == "Sunset Diagram"
    assert img["section_hint"] == "Introduction"
    # generated_images property should be set
    assert gen.generated_images == result
    # Stream output should have recorded generating and ready messages
    assert any("Generating image" in msg or "Generating" in msg for _, _, msg in calls)
    assert any("images ready" in msg.lower() or "images ready" in msg for _, _, msg in calls)


@pytest.mark.asyncio
async def test_plan_and_generate_images_all_fail(monkeypatch):
    # Prevent provider init side-effects
    monkeypatch.setattr(ImageGenerator, "_init_provider", lambda self: None)

    researcher = SimpleNamespace(cfg=SimpleNamespace(image_generation_max_images=2), verbose=True, websocket=None)
    gen = ImageGenerator(researcher)

    monkeypatch.setattr(gen, "is_enabled", lambda: True)

    # Both concepts will fail
    concepts = [
        {"title": "Fail One", "prompt": "fail_me_1", "section_hint": ""},
        {"title": "Fail Two", "prompt": "fail_me_2", "section_hint": ""},
    ]

    async def fake_plan(context, query):
        return concepts
    monkeypatch.setattr(gen, "_plan_image_concepts", fake_plan)

    class AlwaysFailProvider:
        async def generate_image(self, prompt, context="", research_id="", num_images=1, style=None):
            raise RuntimeError("provider consistently fails")

    gen.image_provider = AlwaysFailProvider()

    calls = []

    async def fake_stream_output(channel, event, message, websocket):
        calls.append((channel, event, message))

    module_path = ImageGenerator.__module__
    monkeypatch.setattr(f"{module_path}.stream_output", fake_stream_output)

    result = await gen.plan_and_generate_images("ctx", "query")
    assert result == []
    # generated_images should be set to empty list
    assert gen.generated_images == []
    # Should have emitted an images_failed message
    assert any("No images could be generated" in msg or "No images" in msg for _, _, msg in calls)
