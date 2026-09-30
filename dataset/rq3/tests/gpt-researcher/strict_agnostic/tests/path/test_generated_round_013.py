import asyncio
import json
import re
import pytest

from gpt_researcher.skills import image_generator as ig_mod

# Helper async recorder to capture stream_output calls
class StreamRecorder:
    def __init__(self):
        self.calls = []

    async def __call__(self, channel, event, message, websocket, final=False, data=None):
        # Store a simple serializable snapshot of the call
        self.calls.append({
            "channel": channel,
            "event": event,
            "message": message,
            "websocket": websocket,
            "final": bool(final),
            "data": data,
        })


class DummyResearcher:
    def __init__(self, verbose=False, websocket=None):
        self.verbose = verbose
        self.websocket = websocket
        # Provide a minimal cfg attribute because ImageGenerator.__init__ expects researcher.cfg
        class Cfg:
            image_generation_style = 'dark'
        self.cfg = Cfg()


class DummyProvider:
    def __init__(self, behavior):
        # behavior can be: 'ok' -> return one image, 'empty' -> return [], 'raise' -> raise
        self.behavior = behavior

    async def generate_image(self, prompt, context, research_id, num_images, style):
        # Deterministic behavior depending on the configured flag
        if self.behavior == 'ok':
            return [{
                "url": "http://example.test/img.png",
                "alt_text": "an-example",
            }]
        elif self.behavior == 'empty':
            return []
        else:
            raise RuntimeError("simulated-provider-failure")


def make_generator(monkeypatch, researcher_verbose=False, provider_behavior='ok'):
    # Setup recorder and patch the module-level stream_output used by the implementation
    recorder = StreamRecorder()
    monkeypatch.setattr(ig_mod, 'stream_output', recorder)

    researcher = DummyResearcher(verbose=researcher_verbose, websocket="WS")
    gen = ig_mod.ImageGenerator(researcher)

    # Attach deterministic provider and config
    gen.image_provider = DummyProvider(provider_behavior)

    class Cfg:
        image_generation_style = 'dark'

    gen.cfg = Cfg()
    # Ensure a predictable max_images
    gen.max_images = 5

    return gen, recorder


def test_is_disabled_round_013(monkeypatch):
    # If image generation is disabled, placeholders are removed and no images returned.
    gen, recorder = make_generator(monkeypatch, researcher_verbose=False, provider_behavior='ok')

    # Force is_enabled to return False
    monkeypatch.setattr(gen, 'is_enabled', lambda: False)

    report = "Hello [IMAGE: a lonely cat] world"
    modified_report, images = asyncio.run(gen.process_image_placeholders(report, query="q1", research_id="r1"))

    # The placeholder should be removed and no images produced
    assert "[IMAGE:" not in modified_report
    assert images == []
    # No stream_output calls when disabled
    assert recorder.calls == []


def test_no_placeholders_round_013(monkeypatch):
    # When enabled but no placeholders present, the report is unchanged and no images are produced.
    gen, recorder = make_generator(monkeypatch, researcher_verbose=False, provider_behavior='ok')

    # Ensure is_enabled is True for this instance
    monkeypatch.setattr(gen, 'is_enabled', lambda: True)

    report = "This report has no images."
    modified_report, images = asyncio.run(gen.process_image_placeholders(report, query="q2", research_id="r2"))

    assert modified_report == report
    assert images == []
    # No calls to stream_output since nothing to do and verbose is False
    assert recorder.calls == []


def test_generate_image_success_round_013(monkeypatch):
    # Successful image generation should replace the placeholder with markdown and emit stream events when verbose.
    gen, recorder = make_generator(monkeypatch, researcher_verbose=True, provider_behavior='ok')
    monkeypatch.setattr(gen, 'is_enabled', lambda: True)

    report = "Intro text. [IMAGE: colorful bird on a branch] End."
    modified_report, images = asyncio.run(gen.process_image_placeholders(report, query="birds", research_id="rid"))

    # The generated images list should contain one item with description preserved
    assert len(images) == 1
    assert images[0].get("description") == "colorful bird on a branch"
    assert images[0]["url"] == "http://example.test/img.png"

    # The placeholder should be replaced by markdown referencing the provider's url and alt_text
    assert "![an-example](http://example.test/img.png)" in modified_report

    # Because verbose=True, we should have recorded several stream_output events including
    # image_placeholders_found, image_generating, image_generated, image_generation_complete, and inline_images
    events = [c["event"] for c in recorder.calls]
    assert any(e == "image_placeholders_found" for e in events)
    assert any(e == "image_generating" for e in events)
    assert any(e == "image_generated" for e in events)
    assert any(e == "image_generation_complete" for e in events)
    # The generated images are sent over the 'generated_images' channel with event 'inline_images'
    inline_calls = [c for c in recorder.calls if c["channel"] == "generated_images" and c["event"] == "inline_images"]
    assert len(inline_calls) == 1
    # final flag should be True and data should contain the list of generated images
    assert inline_calls[0]["final"] is True
    assert isinstance(inline_calls[0]["data"], list)
    assert inline_calls[0]["data"][0]["url"] == "http://example.test/img.png"


def test_generate_image_empty_round_013(monkeypatch):
    # If the provider returns an empty list, the placeholder should be removed and no generated images recorded.
    gen, recorder = make_generator(monkeypatch, researcher_verbose=True, provider_behavior='empty')
    monkeypatch.setattr(gen, 'is_enabled', lambda: True)

    report = "Paragraph. [IMAGE: impossible scene] More text."
    modified_report, images = asyncio.run(gen.process_image_placeholders(report, query="q3", research_id="r3"))

    # No images generated
    assert images == []
    # Placeholder should be removed
    assert "[IMAGE:" not in modified_report
    # We should have seen an 'image_generating' event and then a fallback removal (no generated image)
    events = [c["event"] for c in recorder.calls]
    assert any(e == "image_generating" for e in events)


def test_generate_image_failure_round_013(monkeypatch):
    # If the provider raises an exception, placeholder should be removed and an error event emitted when verbose.
    gen, recorder = make_generator(monkeypatch, researcher_verbose=True, provider_behavior='raise')
    monkeypatch.setattr(gen, 'is_enabled', lambda: True)

    report = "Start [IMAGE: will fail] Finish"
    modified_report, images = asyncio.run(gen.process_image_placeholders(report, query="q4", research_id="r4"))

    # No images produced on failure and placeholder removed
    assert images == []
    assert "[IMAGE:" not in modified_report
    # Ensure an image_generation_error event was emitted
    events = [c["event"] for c in recorder.calls]
    assert any(e == "image_generation_error" for e in events)
