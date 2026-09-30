import pytest
import asyncio
from gpt_researcher.skills.image_generator import ImageGenerator


class DummyResearcher:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.websocket = "fake-ws"


@pytest.mark.asyncio
async def test_generate_images_disabled_round_016(monkeypatch):
    """When image generation is disabled, the original report is returned and no stream calls are made."""
    # Build instance without running __init__ to avoid provider initialization side effects
    inst = ImageGenerator.__new__(ImageGenerator)
    inst.researcher = DummyResearcher(verbose=False)
    # Force disabled
    inst.is_enabled = lambda: False

    stream_calls = []

    async def fake_stream(*args, **kwargs):
        stream_calls.append((args, kwargs))

    # Patch the module-level stream_output used in the function under test
    monkeypatch.setattr("gpt_researcher.skills.image_generator.stream_output", fake_stream)

    report = "Original report"
    out_report, images = await inst.generate_images_for_report(report, "query-x")

    assert out_report == report
    assert images == []
    # No stream_output calls should have been made because generation is disabled
    assert stream_calls == []


@pytest.mark.asyncio
async def test_no_suggestions_verbose_round_016(monkeypatch):
    """When analysis returns no suggestions and verbose is True, start and skip stream messages are emitted and result is empty."""
    inst = ImageGenerator.__new__(ImageGenerator)
    inst.researcher = DummyResearcher(verbose=True)
    inst.is_enabled = lambda: True

    stream_calls = []

    async def fake_stream(channel, event, message, websocket, *args):
        # record the channel and event (sufficient to assert behavior)
        stream_calls.append((channel, event, message, websocket, args))

    monkeypatch.setattr("gpt_researcher.skills.image_generator.stream_output", fake_stream)

    async def fake_analyze(report, query):
        return []

    inst.analyze_report_for_images = fake_analyze

    report = "Report with no image sections"
    out_report, images = await inst.generate_images_for_report(report, "query-y")

    assert out_report == report
    assert images == []

    # Expect at least the start and skip events in order
    events = [c[1] for c in stream_calls]
    assert "image_generation_start" in events
    assert "image_generation_skip" in events
    # start should come before skip
    assert events.index("image_generation_start") < events.index("image_generation_skip")


@pytest.mark.asyncio
async def test_mixed_generation_success_and_error_round_016(monkeypatch):
    """Test mixed outcomes: one suggestion fails (raises), another returns an image -> image gets embedded and proper stream events are emitted."""
    inst = ImageGenerator.__new__(ImageGenerator)
    inst.researcher = DummyResearcher(verbose=True)
    inst.is_enabled = lambda: True

    stream_calls = []

    async def fake_stream(channel, event, message, websocket, *args):
        stream_calls.append((channel, event, message, websocket, args))

    monkeypatch.setattr("gpt_researcher.skills.image_generator.stream_output", fake_stream)

    # Two suggestions: first will raise, second will succeed
    suggestions = [
        {"section_header": "Section One", "image_prompt": "p-raise", "section_content": "c1"},
        {"section_header": "Section Two", "image_prompt": "p-ok", "section_content": "c2"},
    ]

    async def fake_analyze(report, query):
        return suggestions

    inst.analyze_report_for_images = fake_analyze

    class DummyProvider:
        async def generate_image(self, prompt, context, research_id, num_images):
            if prompt == "p-raise":
                raise RuntimeError("simulated failure")
            if prompt == "p-ok":
                return [{"url": "http://img.example/u2.png", "alt_text": "alt2"}]
            return []

    inst.image_provider = DummyProvider()

    # patch _embed_images_in_report to check it's called with the generated image and to return a modified report
    embed_called = {}

    def fake_embed(report, images, suggestions_arg):
        embed_called["report"] = report
        embed_called["images"] = images
        embed_called["suggestions"] = suggestions_arg
        return report + " [embedded]"

    inst._embed_images_in_report = fake_embed

    report = "Report that will receive images"
    out_report, generated_images = await inst.generate_images_for_report(report, "query-z", research_id="rid")

    # The embed function should have been called and the returned report should be modified
    assert out_report.endswith("[embedded]")
    # Only one successful generated image expected
    assert isinstance(generated_images, list)
    assert len(generated_images) == 1
    assert generated_images[0]["url"] == "http://img.example/u2.png"
    # The appended section_header should have been added by the code path that handles images
    assert generated_images[0]["section_header"] == "Section Two"

    # Verify stream events included an error (from first suggestion) and image_generated and image_generation_complete
    events = [c[1] for c in stream_calls]
    assert any(e == "image_generation_error" for e in events), f"events missing error: {events}"
    assert any(e == "image_generated" for e in events), f"events missing image_generated: {events}"
    assert any(e == "image_generation_complete" for e in events), f"events missing complete: {events}"

    # Ensure the generated_images payload was also emitted via the 'generated_images' channel
    channels = [c[0] for c in stream_calls]
    assert "generated_images" in channels

    # Confirm embed received the same generated_images list
    assert embed_called["images"] == generated_images
