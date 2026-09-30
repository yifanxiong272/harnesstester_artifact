import asyncio
import json
from types import SimpleNamespace
import importlib

import pytest

# Import the module under test
img_mod = importlib.import_module('gpt_researcher.skills.image_generator')

# Helper to create dummy self that has the attributes/methods the method expects
class DummySelf:
    def __init__(self, *, enabled=True, max_images=10, verbose=False, style=None, provider=None):
        # is_enabled is a callable in the original class
        self._enabled = enabled
        self.max_images = max_images
        self.researcher = SimpleNamespace(verbose=verbose, websocket=object())
        # cfg object must exist for getattr(self.cfg, 'image_generation_style', 'dark')
        if style is None:
            # omit custom style to exercise the getattr default
            self.cfg = SimpleNamespace()
        else:
            self.cfg = SimpleNamespace(image_generation_style=style)
        # image_provider must expose async generate_image
        if provider is None:
            # default provider that returns nothing
            async def gen_image(**kwargs):
                return []
            self.image_provider = SimpleNamespace(generate_image=gen_image)
        else:
            self.image_provider = provider
        # placeholder for assigned generated_images
        self.generated_images = None

    def is_enabled(self):
        return self._enabled


# A small async stream_output recorder used to patch the real stream_output
class StreamRecorder:
    def __init__(self):
        self.calls = []

    async def __call__(self, *args, **kwargs):
        # Record a tuple of (args, kwargs) for assertions
        self.calls.append((args, kwargs))
        # Return a resolved coroutine
        return None


def test_disabled_removes_placeholders_round_013(monkeypatch):
    """When image generation is disabled, placeholders are removed and no images returned."""
    recorder = StreamRecorder()
    # Patch stream_output so the function exists but shouldn't be used when disabled
    monkeypatch.setattr(img_mod, 'stream_output', recorder)

    s = DummySelf(enabled=False)
    report = "Prefix [IMAGE: a description] Suffix"

    modified_report, images = asyncio.run(
        img_mod.ImageGenerator.process_image_placeholders(s, report, "query1")
    )

    # Placeholders removed and no images produced
    assert images == []
    assert "[IMAGE:" not in modified_report
    assert "Prefix" in modified_report and "Suffix" in modified_report
    # stream_output should not have been called when disabled
    assert recorder.calls == []


def test_no_placeholders_returns_same_report_round_013(monkeypatch):
    """If enabled but there are no placeholders, the report is returned unchanged and images empty."""
    recorder = StreamRecorder()
    monkeypatch.setattr(img_mod, 'stream_output', recorder)

    s = DummySelf(enabled=True, verbose=False, max_images=2)
    report = "This report contains no images."

    modified_report, images = asyncio.run(
        img_mod.ImageGenerator.process_image_placeholders(s, report, "query2")
    )

    assert modified_report == report
    assert images == []
    # verbose is False, so no stream_output calls
    assert recorder.calls == []


def test_image_generated_success_round_013(monkeypatch):
    """When provider returns an image, the placeholder is replaced with markdown and image metadata set."""
    recorder = StreamRecorder()
    monkeypatch.setattr(img_mod, 'stream_output', recorder)

    # provider that returns one image dict
    async def gen_image(**kwargs):
        # Validate that prompt and context are passed deterministically
        assert 'prompt' in kwargs and 'context' in kwargs
        # Return the provider shape expected by the method
        return [{'url': 'http://example.com/img.png', 'alt_text': 'ExampleAlt'}]

    provider = SimpleNamespace(generate_image=gen_image)
    s = DummySelf(enabled=True, verbose=True, provider=provider, style='light', max_images=3)

    report = "Start [IMAGE: colorful abstract art] End"

    modified_report, images = asyncio.run(
        img_mod.ImageGenerator.process_image_placeholders(s, report, "the-query", research_id="R1")
    )

    # One image generated and embedded in markdown
    assert len(images) == 1
    img = images[0]
    # The provider result should be augmented with the original description
    assert img['url'] == 'http://example.com/img.png'
    assert img['alt_text'] == 'ExampleAlt'
    assert img['description'] == 'colorful abstract art'

    # The report must now contain the markdown image with the absolute URL
    assert '![ExampleAlt](http://example.com/img.png)' in modified_report

    # The instance attribute generated_images should be set to the same list
    assert s.generated_images == images

    # Ensure stream_output was called for several lifecycle events (placeholders found, generating, generated, complete, generated_images)
    event_names = [call[0][1] if len(call[0]) > 1 else None for call in recorder.calls]
    # Expect at least these events to be in the recorded calls
    assert 'image_placeholders_found' in event_names
    assert 'image_generating' in event_names
    assert 'image_generated' in event_names
    assert 'image_generation_complete' in event_names
    assert 'inline_images' in event_names


def test_image_generation_returns_empty_and_removes_placeholder_round_013(monkeypatch):
    """If provider returns empty list, placeholder is removed and no images are returned."""
    recorder = StreamRecorder()
    monkeypatch.setattr(img_mod, 'stream_output', recorder)

    async def gen_none(**kwargs):
        return []

    provider = SimpleNamespace(generate_image=gen_none)
    s = DummySelf(enabled=True, verbose=True, provider=provider, max_images=2)

    report = "Before [IMAGE: nothing came out] After"

    modified_report, images = asyncio.run(
        img_mod.ImageGenerator.process_image_placeholders(s, report, "query3")
    )

    assert images == []
    # Placeholder removed
    assert '[IMAGE:' not in modified_report
    # Because nothing was generated, the 'inline_images' send should NOT be invoked
    event_names = [call[0][1] if len(call[0]) > 1 else None for call in recorder.calls]
    assert 'inline_images' not in event_names


def test_image_provider_raises_exception_streams_error_round_013(monkeypatch):
    """If the image provider raises, the placeholder is removed and an error stream event is emitted when verbose."""
    recorder = StreamRecorder()
    monkeypatch.setattr(img_mod, 'stream_output', recorder)

    async def gen_bad(**kwargs):
        raise RuntimeError('boom')

    provider = SimpleNamespace(generate_image=gen_bad)
    s = DummySelf(enabled=True, verbose=True, provider=provider, max_images=1)

    report = "X [IMAGE: will fail] Y"

    modified_report, images = asyncio.run(
        img_mod.ImageGenerator.process_image_placeholders(s, report, "query4")
    )

    # Placeholder removed despite exception
    assert '[IMAGE:' not in modified_report
    # No generated images
    assert images == []

    # Check that an error reporting event was streamed
    # Find any call where the event name equals 'image_generation_error'
    found_error = any((len(args) > 1 and args[1] == 'image_generation_error') for (args, kw) in recorder.calls)
    assert found_error, 'Expected stream_output to be called with image_generation_error event'
