import pytest
import types
from gpt_researcher.skills import image_generator as img_mod
from gpt_researcher.skills.image_generator import ImageGenerator

# Shared fake stream_output to capture calls deterministically
_stream_calls = []

async def _fake_stream_output(channel, event, message, websocket, *args, **kwargs):
    # Record minimal, deterministic details for assertions
    _stream_calls.append({
        "channel": channel,
        "event": event,
        "message": str(message),
        "websocket": websocket,
    })

# Patch the module-level stream_output used by ImageGenerator
img_mod.stream_output = _fake_stream_output

class DummyResearcher:
    def __init__(self, verbose=False, websocket=None, cfg=None):
        # Minimal attributes required by ImageGenerator.__init__
        # The real ImageGenerator expects researcher.cfg to exist.
        self.verbose = verbose
        self.websocket = websocket
        # Provide a minimal config dict to satisfy attribute access during initialization
        self.cfg = {} if cfg is None else cfg

@pytest.mark.asyncio
async def test_disabled_image_generation_round_016():
    """When image generation is disabled, the function should return the original report and no images."""
    _stream_calls.clear()
    researcher = DummyResearcher(verbose=False, websocket=None)
    gen = ImageGenerator(researcher)

    # Force disabled path
    gen.is_enabled = lambda: False

    report_text = "Original report"
    out_report, out_images = await gen.generate_images_for_report(report_text, "query")

    assert out_report == report_text
    assert out_images == []
    # No stream events should be emitted when disabled
    assert _stream_calls == []

@pytest.mark.asyncio
async def test_no_suggestions_round_016():
    """When analyze_report_for_images yields no suggestions, return original report and empty images."""
    _stream_calls.clear()
    researcher = DummyResearcher(verbose=False, websocket=None)
    gen = ImageGenerator(researcher)

    # Enable generation but simulate no suggestions
    gen.is_enabled = lambda: True

    async def _fake_analyze(report, query):
        return []

    gen.analyze_report_for_images = _fake_analyze
    # image_provider should not be called, but provide a harmless placeholder
    gen.image_provider = types.SimpleNamespace(generate_image=lambda *a, **k: [])

    report_text = "Report without image-worthy sections"
    out_report, out_images = await gen.generate_images_for_report(report_text, "query")

    assert out_report == report_text
    assert out_images == []
    # verbose is False so no stream events
    assert _stream_calls == []

@pytest.mark.asyncio
async def test_generate_and_embed_images_round_016():
    """Happy path: suggestions present, image provider returns an image, images are embedded and metadata updated."""
    _stream_calls.clear()
    researcher = DummyResearcher(verbose=True, websocket="ws://dummy")
    gen = ImageGenerator(researcher)

    # Enable generation
    gen.is_enabled = lambda: True

    suggestions = [
        {
            "image_prompt": "A diagram of a pipeline",
            "section_content": "Detailed section content",
            "section_header": "Pipeline Architecture",
        }
    ]

    async def _fake_analyze(report, query):
        return suggestions

    async def _fake_generate_image(prompt, context, research_id=None, num_images=1):
        # Return a single image dict as the real provider would
        return [{"url": "http://example.com/img.png", "alt_text": "diagram image"}]

    # Deterministic embed function: append a marker so we can assert embedding happened
    def _fake_embed(report, images, suggestions_arg):
        return report + "\n[EMBEDDED_IMAGES]"

    gen.analyze_report_for_images = _fake_analyze
    gen.image_provider = types.SimpleNamespace(generate_image=_fake_generate_image)
    gen._embed_images_in_report = _fake_embed

    report_text = "Report that will get images"
    out_report, out_images = await gen.generate_images_for_report(report_text, "query", research_id="rid")

    # Embedding happened
    assert out_report.endswith("[EMBEDDED_IMAGES]")
    # One image generated and returned
    assert len(out_images) == 1
    # The generator should have attached the section_header to the image dict
    assert out_images[0]["section_header"] == "Pipeline Architecture"
    # generated_images attribute should reference the same list
    assert gen.generated_images is out_images

    # Verify that at least one informative stream event about completion was emitted
    events = [c["event"] for c in _stream_calls]
    assert any("image_generation_complete" == e for e in events) or any("image_generated" == e for e in events)

@pytest.mark.asyncio
async def test_image_provider_exception_round_016():
    """When the image provider raises an exception, the generator should continue and emit an error stream event."""
    _stream_calls.clear()
    researcher = DummyResearcher(verbose=True, websocket="ws://dummy")
    gen = ImageGenerator(researcher)

    gen.is_enabled = lambda: True

    suggestions = [
        {
            "image_prompt": "Prompt that will fail",
            "section_content": "content",
            "section_header": "Failing Section",
        }
    ]

    async def _fake_analyze(report, query):
        return suggestions

    async def _failing_generate_image(prompt, context, research_id=None, num_images=1):
        raise RuntimeError("simulated provider failure")

    gen.analyze_report_for_images = _fake_analyze
    gen.image_provider = types.SimpleNamespace(generate_image=_failing_generate_image)

    report_text = "Report where generation fails"
    out_report, out_images = await gen.generate_images_for_report(report_text, "query")

    # On failure, nothing should be embedded and images list should be empty
    assert out_images == []
    assert out_report == report_text

    # There should be an error-related stream event recorded when verbose=True
    events = [c["event"] for c in _stream_calls]
    assert any("image_generation_error" == e for e in events)
