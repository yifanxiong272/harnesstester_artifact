import asyncio
import pytest
from types import SimpleNamespace

import gpt_researcher.skills.image_generator as immod
from gpt_researcher.skills.image_generator import ImageGenerator


class DummyCfg:
    pass


class DummyResearcher:
    def __init__(self, cfg, verbose=False):
        self.cfg = cfg
        self.verbose = verbose
        self.websocket = "fake-ws"


@pytest.mark.asyncio
async def test_plan_and_generate_images_disabled_round_022():
    """When image generation is disabled, the method should return an empty list."""
    cfg = DummyCfg()
    cfg.IMAGE_GENERATION_ENABLED = False
    researcher = DummyResearcher(cfg, verbose=False)

    gen = ImageGenerator(researcher)

    res = await gen.plan_and_generate_images("some context", "query")
    assert res == []
    # ensure generated_images also set to empty
    assert getattr(gen, "generated_images", []) == []


@pytest.mark.asyncio
async def test_plan_and_generate_images_no_concepts_verbose_round_022(monkeypatch):
    """When enabled but planner returns no concepts, returns [] and emits planning log if verbose."""
    cfg = DummyCfg()
    cfg.IMAGE_GENERATION_ENABLED = False
    researcher = DummyResearcher(cfg, verbose=True)

    gen = ImageGenerator(researcher)
    # inject a fake available provider so is_enabled() returns True
    fake_provider = SimpleNamespace()
    fake_provider.is_available = lambda: True
    gen.image_provider = fake_provider

    # capture stream_output calls
    calls = []

    async def fake_stream_output(stream, tag, message, websocket):
        calls.append((stream, tag, message, websocket))

    monkeypatch.setattr(immod, "stream_output", fake_stream_output)

    # planner returns no concepts
    async def fake_plan(context, query):
        return []

    monkeypatch.setattr(gen, "_plan_image_concepts", fake_plan)

    res = await gen.plan_and_generate_images("ctx", "q")
    assert res == []

    # Expect at least the initial planning stream_output call when verbose
    assert any(call[1] == "image_planning" for call in calls), f"calls: {calls}"


@pytest.mark.asyncio
async def test_plan_and_generate_images_generate_success_and_verbose_round_022(monkeypatch):
    """When planning yields concepts and provider returns images, titles and section_hint are set and images_ready is emitted."""
    cfg = DummyCfg()
    cfg.IMAGE_GENERATION_ENABLED = False
    cfg.image_generation_style = "light"
    researcher = DummyResearcher(cfg, verbose=True)

    gen = ImageGenerator(researcher)
    # inject fake available provider with a successful generate_image
    async def fake_generate_image(prompt, context, research_id, num_images, style):
        return [{"url": f"http://img/{prompt}", "provider_meta": True}]

    fake_provider = SimpleNamespace()
    fake_provider.is_available = lambda: True
    fake_provider.generate_image = fake_generate_image
    gen.image_provider = fake_provider

    # plan returns two concepts
    concepts = [
        {"title": "Concept One", "prompt": "one prompt", "section_hint": "sec1"},
        {"title": "Concept Two", "prompt": "two prompt", "section_hint": "sec2"},
    ]

    async def fake_plan(context, query):
        return concepts

    monkeypatch.setattr(gen, "_plan_image_concepts", fake_plan)

    # capture stream_output calls
    calls = []

    async def fake_stream_output(stream, tag, message, websocket):
        calls.append((stream, tag, message, websocket))

    monkeypatch.setattr(immod, "stream_output", fake_stream_output)

    res = await gen.plan_and_generate_images("ctx", "q", research_id="R1")

    # Two concepts -> two generated images
    assert isinstance(res, list)
    assert len(res) == 2

    # Each result should carry the concept title and section_hint set by generate_single_image
    titles = [r["title"] for r in res]
    hints = [r.get("section_hint", None) for r in res]
    assert titles == ["Concept One", "Concept Two"]
    assert hints == ["sec1", "sec2"]

    # internal state updated
    assert gen.generated_images == res

    # last stream_output should be images_ready when generation succeeded
    assert any(call[1] == "images_ready" for call in calls), f"calls: {calls}"


@pytest.mark.asyncio
async def test_plan_and_generate_images_all_fail_verbose_round_022(monkeypatch):
    """When generation fails (exceptions or empty returns), the method returns [] and emits images_failed."""
    cfg = DummyCfg()
    cfg.IMAGE_GENERATION_ENABLED = False
    researcher = DummyResearcher(cfg, verbose=True)

    gen = ImageGenerator(researcher)
    # fake provider that raises for any generate image call
    async def raising_generate_image(prompt, context, research_id, num_images, style):
        raise RuntimeError("simulated provider error")

    fake_provider = SimpleNamespace()
    fake_provider.is_available = lambda: True
    fake_provider.generate_image = raising_generate_image
    gen.image_provider = fake_provider

    # return two concepts so both attempts fail
    concepts = [
        {"title": "C1", "prompt": "p1"},
        {"title": "C2", "prompt": "p2"},
    ]

    async def fake_plan(context, query):
        return concepts

    monkeypatch.setattr(gen, "_plan_image_concepts", fake_plan)

    # capture stream_output calls
    calls = []

    async def fake_stream_output(stream, tag, message, websocket):
        calls.append((stream, tag, message, websocket))

    monkeypatch.setattr(immod, "stream_output", fake_stream_output)

    res = await gen.plan_and_generate_images("ctx", "q")

    assert res == []
    # images_failed should be emitted when all generators fail
    assert any(call[1] == "images_failed" for call in calls), f"calls: {calls}"
