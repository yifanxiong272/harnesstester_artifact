# file: gpt_researcher/skills/image_generator.py:77-180
# asked: {"lines": [97, 98, 99, 101, 102, 103, 104, 105, 106, 110, 112, 113, 114, 116, 117, 118, 119, 120, 121, 125, 127, 129, 130, 131, 132, 133, 134, 135, 138, 139, 140, 141, 142, 143, 146, 147, 148, 149, 150, 152, 153, 154, 157, 158, 161, 162, 164, 165, 166, 167, 168, 169, 170, 173, 174, 175, 176, 177, 180], "branches": [[97, 98], [97, 101], [101, 102], [101, 110], [112, 113], [112, 116], [116, 117], [116, 125], [130, 131], [130, 138], [146, 147], [146, 154], [164, 165], [164, 180], [165, 166], [165, 173]]}
# gained: {"lines": [97, 98, 99, 101, 102, 103, 104, 105, 106, 110, 112, 113, 114, 116, 117, 118, 119, 120, 121, 125, 127, 129, 130, 131, 132, 133, 134, 135, 138, 139, 140, 141, 142, 143, 146, 147, 148, 149, 150, 152, 153, 154, 157, 158, 161, 162, 164, 165, 166, 167, 168, 169, 170, 173, 174, 175, 176, 177, 180], "branches": [[97, 98], [97, 101], [101, 102], [112, 113], [112, 116], [116, 117], [130, 131], [146, 147], [164, 165], [165, 166], [165, 173]]}

import types
import pytest

@pytest.mark.asyncio
async def test_plan_and_generate_images_disabled(monkeypatch):
    from gpt_researcher.skills import image_generator

    # Create a minimal researcher object
    researcher = types.SimpleNamespace(cfg=types.SimpleNamespace(image_generation_max_images=3), verbose=False, websocket=None)
    gen = image_generator.ImageGenerator(researcher)

    # Force is_enabled to be False
    monkeypatch.setattr(gen, "is_enabled", lambda: False)

    # Patch stream_output to detect any calls (should not be called)
    called = []
    async def fake_stream(*args, **kwargs):
        called.append((args, kwargs))
    monkeypatch.setattr(image_generator, "stream_output", fake_stream)

    result = await gen.plan_and_generate_images("some context", "some query")
    assert result == []
    assert called == []  # stream_output must not have been called


@pytest.mark.asyncio
async def test_plan_and_generate_images_no_concepts_verbose(monkeypatch):
    from gpt_researcher.skills import image_generator

    # Verbose researcher
    researcher = types.SimpleNamespace(
        cfg=types.SimpleNamespace(image_generation_max_images=3, image_generation_style='dark'),
        verbose=True,
        websocket="ws"
    )
    gen = image_generator.ImageGenerator(researcher)

    # Enable generation
    monkeypatch.setattr(gen, "is_enabled", lambda: True)

    # _plan_image_concepts returns empty list -> should short-circuit and return []
    async def fake_plan(context, query):
        return []
    monkeypatch.setattr(gen, "_plan_image_concepts", fake_plan)

    outputs = []
    async def fake_stream(stream, event, message, websocket):
        outputs.append((stream, event, message, websocket))
    monkeypatch.setattr(image_generator, "stream_output", fake_stream)

    result = await gen.plan_and_generate_images("ctx", "query")
    assert result == []
    # The analyzer message should have been sent at the start (since verbose is True)
    assert any("Analyzing research context" in msg for (_, _, msg, _) in outputs)


@pytest.mark.asyncio
async def test_plan_and_generate_images_mixed_success_and_failure(monkeypatch):
    from gpt_researcher.skills import image_generator

    researcher = types.SimpleNamespace(
        cfg=types.SimpleNamespace(image_generation_max_images=3, image_generation_style='bright'),
        verbose=True,
        websocket="ws"
    )
    gen = image_generator.ImageGenerator(researcher)

    monkeypatch.setattr(gen, "is_enabled", lambda: True)

    # Two concepts: first will succeed, second will raise to trigger exception path
    concepts = [
        {'title': 'First concept', 'prompt': 'prompt1', 'section_hint': 'hint1'},
        {'title': 'Second concept', 'prompt': 'prompt2'},
    ]
    async def fake_plan(context, query):
        return concepts
    monkeypatch.setattr(gen, "_plan_image_concepts", fake_plan)

    class FakeProvider:
        async def generate_image(self, prompt, context, research_id, num_images, style):
            if 'prompt1' in prompt:
                return [{'url': 'u1'}]
            raise RuntimeError("generation failed")
    gen.image_provider = FakeProvider()

    outputs = []
    async def fake_stream(stream, event, message, websocket):
        outputs.append((stream, event, message, websocket))
    monkeypatch.setattr(image_generator, "stream_output", fake_stream)

    result = await gen.plan_and_generate_images("ctx", "query", research_id="rid123")
    # One image should be produced and properly annotated
    assert isinstance(result, list)
    assert len(result) == 1
    img = result[0]
    assert img['url'] == 'u1'
    assert img['title'] == 'First concept'
    assert img['section_hint'] == 'hint1'

    messages = [m for (_, _, m, _) in outputs]
    assert any("Analyzing research context" in m for m in messages)
    assert any("Identified" in m for m in messages)
    assert any("Generating image" in m for m in messages)
    # images_ready message should be present
    assert any("images ready" in m.lower() or "images ready" in m for m in messages)


@pytest.mark.asyncio
async def test_plan_and_generate_images_all_failures_triggers_images_failed(monkeypatch):
    from gpt_researcher.skills import image_generator

    researcher = types.SimpleNamespace(
        cfg=types.SimpleNamespace(image_generation_max_images=3, image_generation_style='dark'),
        verbose=True,
        websocket="ws"
    )
    gen = image_generator.ImageGenerator(researcher)

    monkeypatch.setattr(gen, "is_enabled", lambda: True)

    # Two concepts but provider will fail for both
    concepts = [
        {'title': 'C1', 'prompt': 'p1'},
        {'title': 'C2', 'prompt': 'p2'},
    ]
    async def fake_plan(context, query):
        return concepts
    monkeypatch.setattr(gen, "_plan_image_concepts", fake_plan)

    class AlwaysFailProvider:
        async def generate_image(self, prompt, context, research_id, num_images, style):
            raise RuntimeError("always fail")
    gen.image_provider = AlwaysFailProvider()

    outputs = []
    async def fake_stream(stream, event, message, websocket):
        outputs.append((stream, event, message, websocket))
    monkeypatch.setattr(image_generator, "stream_output", fake_stream)

    result = await gen.plan_and_generate_images("ctx", "query")
    # No images should be returned
    assert result == []

    # Ensure the "No images could be generated" message was sent
    messages = [m for (_, _, m, _) in outputs]
    assert any("No images could be generated" in m for m in messages)
