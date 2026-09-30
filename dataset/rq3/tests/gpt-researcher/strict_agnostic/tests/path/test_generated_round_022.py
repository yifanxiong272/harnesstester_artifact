import asyncio
from types import SimpleNamespace
import gpt_researcher.skills.image_generator as imgmod

# Helper to run the async method under test as a bound method on a lightweight instance
def _make_instance(**attrs):
    inst = SimpleNamespace()
    for k, v in attrs.items():
        setattr(inst, k, v)
    return inst

def test_plan_and_generate_images_disabled_round_022():
    """If image generation is disabled, the function should return an empty list and not attempt generation."""
    calls = []

    async def fake_stream_output(*args, **kwargs):
        calls.append((args, kwargs))

    # Patch stream_output in the module to ensure no external effects
    imgmod.stream_output = fake_stream_output

    # Build an instance where is_enabled returns False
    inst = _make_instance()
    inst.is_enabled = lambda: False
    # researcher exists but irrelevant because disabled path should short-circuit
    inst.researcher = SimpleNamespace(verbose=True, websocket=None)
    inst.cfg = SimpleNamespace(image_generation_style="dark")

    result = asyncio.run(imgmod.ImageGenerator.plan_and_generate_images(inst, "ctx", "q", research_id="r1"))

    assert result == []
    # No stream output should have been called because the method returns early
    assert calls == []


def test_plan_and_generate_images_no_concepts_round_022():
    """When planning yields no image concepts, the method returns [] and logs appropriately."""
    calls = []

    async def fake_stream_output(channel, event, message, websocket):
        # capture the event and a short message snippet for assertions
        calls.append((channel, event, str(message)))

    imgmod.stream_output = fake_stream_output

    # Instance where enabled and verbose -> should call stream_output during planning
    async def plan_empty(context, query):
        return []

    inst = _make_instance()
    inst.is_enabled = lambda: True
    inst.researcher = SimpleNamespace(verbose=True, websocket=None)
    inst.cfg = SimpleNamespace(image_generation_style="dark")
    inst._plan_image_concepts = plan_empty
    # image_provider unused in this branch
    inst.image_provider = SimpleNamespace()

    result = asyncio.run(imgmod.ImageGenerator.plan_and_generate_images(inst, "ctx", "q"))

    assert result == []
    # Expect at least one stream_output call for the 'image_planning' message
    assert any(ev == "image_planning" for (_, ev, _) in calls), "planning log was not emitted"


def test_plan_and_generate_images_some_success_round_022():
    """When some images generate successfully and some fail, the successful images are returned and stored."""
    calls = []

    async def fake_stream_output(channel, event, message, websocket):
        calls.append((channel, event, str(message)))

    imgmod.stream_output = fake_stream_output

    # Two concepts: first will succeed, second will raise an exception
    async def plan_two(context, query):
        return [
            {"title": "Concept One", "prompt": "prompt one", "section_hint": "sec1"},
            {"title": "Concept Two", "prompt": "prompt two", "section_hint": "sec2"},
        ]

    async def generate_image_success(prompt, context, research_id, num_images, style):
        # return a list with a single image dict as expected by the implementation
        return [{"url": "http://img/1.png", "meta": {"p": prompt}}]

    async def generate_image_fail(prompt, context, research_id, num_images, style):
        raise RuntimeError("provider failure")

    # image_provider that dispatches based on prompt content
    class FakeProvider:
        async def generate_image(self, prompt, context=None, research_id=None, num_images=1, style=None):
            if "one" in prompt:
                return await generate_image_success(prompt, context, research_id, num_images, style)
            return await generate_image_fail(prompt, context, research_id, num_images, style)

    inst = _make_instance()
    inst.is_enabled = lambda: True
    inst.researcher = SimpleNamespace(verbose=True, websocket=None)
    inst.cfg = SimpleNamespace(image_generation_style="bright")
    inst._plan_image_concepts = plan_two
    inst.image_provider = FakeProvider()

    result = asyncio.run(imgmod.ImageGenerator.plan_and_generate_images(inst, "ctx", "q", research_id="r-42"))

    # One successful image expected
    assert isinstance(result, list)
    assert len(result) == 1
    img = result[0]
    # ensure the provider's returned dict is augmented with title and section_hint
    assert img["url"] == "http://img/1.png"
    assert img["title"] == "Concept One"
    assert img["section_hint"] == "sec1"
    # instance.generated_images should be set accordingly
    assert getattr(inst, "generated_images") == result
    # Ensure final stream_output path for images_ready was triggered
    assert any(ev == "images_ready" for (_, ev, _) in calls), "images_ready log was not emitted"


def test_plan_and_generate_images_all_fail_round_022():
    """When no images can be generated, the method returns an empty list and emits the failure log path."""
    calls = []

    async def fake_stream_output(channel, event, message, websocket):
        calls.append((channel, event, str(message)))

    imgmod.stream_output = fake_stream_output

    # Two concepts but provider returns empty list (no images) for both
    async def plan_two(context, query):
        return [
            {"title": "C1", "prompt": "p1"},
            {"title": "C2", "prompt": "p2"},
        ]

    class EmptyProvider:
        async def generate_image(self, prompt, context=None, research_id=None, num_images=1, style=None):
            # Return empty list to simulate provider not producing any images
            return []

    inst = _make_instance()
    inst.is_enabled = lambda: True
    inst.researcher = SimpleNamespace(verbose=True, websocket=None)
    inst.cfg = SimpleNamespace(image_generation_style="dark")
    inst._plan_image_concepts = plan_two
    inst.image_provider = EmptyProvider()

    result = asyncio.run(imgmod.ImageGenerator.plan_and_generate_images(inst, "ctx", "q"))

    # No images generated
    assert result == []
    # instance.generated_images should be an empty list
    assert getattr(inst, "generated_images") == []
    # Ensure the images_failed event was emitted
    assert any(ev == "images_failed" for (_, ev, _) in calls), "images_failed log was not emitted"
