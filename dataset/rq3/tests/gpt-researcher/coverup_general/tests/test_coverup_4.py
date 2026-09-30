# file: gpt_researcher/skills/image_generator.py:467-585
# asked: {"lines": [486, 487, 488, 491, 492, 493, 494, 495, 496, 500, 502, 503, 504, 505, 506, 507, 508, 509, 511, 513, 514, 515, 516, 517, 518, 522, 523, 524, 525, 526, 527, 528, 529, 532, 533, 534, 535, 536, 537, 540, 541, 542, 543, 545, 546, 547, 548, 549, 550, 552, 553, 554, 555, 556, 557, 558, 559, 563, 564, 565, 567, 568, 569, 570, 571, 572, 576, 577, 578, 579, 580, 581, 582, 585], "branches": [[486, 487], [486, 491], [491, 492], [491, 500], [502, 503], [502, 513], [504, 505], [504, 511], [513, 514], [513, 522], [523, 524], [523, 563], [524, 525], [524, 532], [540, 523], [540, 541], [545, 523], [545, 546], [554, 523], [554, 555], [563, 564], [563, 585], [567, 568], [567, 585]]}
# gained: {"lines": [486, 487, 488, 491, 492, 493, 494, 495, 496, 500, 502, 503, 504, 505, 506, 507, 508, 509, 511, 513, 514, 515, 516, 517, 518, 522, 523, 524, 525, 526, 527, 528, 529, 532, 533, 534, 535, 536, 537, 540, 541, 542, 543, 545, 546, 547, 548, 549, 550, 552, 553, 554, 555, 556, 557, 558, 559, 563, 564, 565, 567, 568, 569, 570, 571, 572, 576, 577, 578, 579, 580, 581, 582, 585], "branches": [[486, 487], [486, 491], [491, 492], [502, 503], [502, 513], [504, 505], [513, 514], [523, 524], [523, 563], [524, 525], [540, 541], [545, 546], [554, 555], [563, 564], [567, 568]]}

import asyncio
import importlib
import json
import types

import pytest


async def _noop_stream_output(*args, **kwargs):
    # default no-op async function
    return None


def _import_image_generator_module():
    """
    Try importing the image_generator module with two likely package paths.
    Raise ImportError if neither is present.
    """
    names_to_try = [
        "gpt_researcher.skills.image_generator",
        "gpt_researcher.gpt_researcher.skills.image_generator",
    ]
    last_err = None
    for name in names_to_try:
        try:
            return importlib.import_module(name)
        except Exception as e:
            last_err = e
    raise last_err


@pytest.mark.asyncio
async def test_generate_images_skips_when_disabled(monkeypatch):
    """
    Covers lines 486-488 where is_enabled() returns False.
    """
    module = _import_image_generator_module()
    ImageGenerator = module.ImageGenerator

    # capture stream_output calls to ensure none are made
    calls = []

    async def fake_stream_output(*args, **kwargs):
        calls.append((args, kwargs))

    # monkeypatch the stream_output used in the module
    monkeypatch.setattr(module, "stream_output", fake_stream_output)

    class DummyGen(ImageGenerator):
        def __init__(self):
            # do not call super().__init__ to avoid side effects
            self.researcher = types.SimpleNamespace(verbose=False, websocket=None)
            self.image_provider = types.SimpleNamespace()

        def is_enabled(self):
            return False

    gen = DummyGen()
    report = "Original report content"
    new_report, images = await gen.generate_images_for_report(report, "query")
    assert new_report == report
    assert images == []
    # ensure no stream_output calls were made
    assert calls == []


@pytest.mark.asyncio
async def test_generate_images_no_suggestions_verbose(monkeypatch):
    """
    Covers the branch where analyze_report_for_images returns no suggestions,
    and researcher.verbose is True, which triggers stream_output calls for start and skip.
    This hits lines 491-511.
    """
    module = _import_image_generator_module()
    ImageGenerator = module.ImageGenerator

    calls = []

    async def fake_stream_output(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(module, "stream_output", fake_stream_output)

    class DummyGen(ImageGenerator):
        def __init__(self):
            self.researcher = types.SimpleNamespace(verbose=True, websocket="ws1")
            self.image_provider = types.SimpleNamespace()

        def is_enabled(self):
            return True

        async def analyze_report_for_images(self, report, query):
            # return empty list to hit the "no sections identified" branch
            return []

    gen = DummyGen()
    report = "Report without imageable sections"
    new_report, images = await gen.generate_images_for_report(report, "query", research_id="rid")
    assert new_report == report
    assert images == []
    # Expect at least two stream_output calls: start and skip
    # First call should have event "image_generation_start", second should include "image_generation_skip"
    assert len(calls) >= 2
    first_args, _ = calls[0]
    second_args, _ = calls[1]
    assert "image_generation_start" in first_args
    assert "image_generation_skip" in second_args


@pytest.mark.asyncio
async def test_generate_images_success_and_error_branches(monkeypatch):
    """
    Covers the main loop where:
    - a successful image generation appends to generated_images and triggers streams (lines 532-552, 563-582)
    - a failed image generation raises and triggers the except block (lines 552-559)
    Also covers embedding via _embed_images_in_report and sending generated_images as JSON over stream.
    """
    module = _import_image_generator_module()
    ImageGenerator = module.ImageGenerator

    stream_calls = []

    async def fake_stream_output(event_type, event_name, message, websocket, send_json=False, payload=None):
        # record key details for assertions
        stream_calls.append(
            {
                "event_type": event_type,
                "event_name": event_name,
                "message": message,
                "websocket": websocket,
                "send_json": send_json,
                "payload": payload,
            }
        )

    monkeypatch.setattr(module, "stream_output", fake_stream_output)

    class DummyImageProvider:
        def __init__(self):
            self.calls = []

        async def generate_image(self, prompt, context, research_id, num_images=1):
            # If prompt contains "RAISE" simulate an exception
            self.calls.append({"prompt": prompt, "context": context, "research_id": research_id})
            if "RAISE" in prompt:
                raise RuntimeError("simulated generation failure")
            # return a typical image info dict list
            return [{"url": f"https://images/{prompt.replace(' ', '_')}.png", "alt_text": f"alt for {prompt}"}]

    class DummyGen(ImageGenerator):
        def __init__(self):
            self.researcher = types.SimpleNamespace(verbose=True, websocket="ws-socket")
            self.image_provider = DummyImageProvider()
            self.generated_images = []

        def is_enabled(self):
            return True

        async def analyze_report_for_images(self, report, query):
            # return two suggestions, one that will succeed and one that will raise
            return [
                {
                    "section_header": "Good Section",
                    "image_prompt": "A nice diagram",
                    "section_content": "content for good section",
                },
                {
                    "section_header": "Bad Section",
                    "image_prompt": "RAISE this will fail",
                    "section_content": "content for bad section",
                },
            ]

        def _embed_images_in_report(self, report, generated_images, suggestions):
            # simple embed: append markdown image links to the report for each generated image
            appended = report
            for img in generated_images:
                appended += f"\n![{img.get('alt_text','')}]({img.get('url')}) <!--{img.get('section_header')}-->"
            return appended

    gen = DummyGen()
    original_report = "Report that will get one image"
    new_report, images = await gen.generate_images_for_report(original_report, "query-xyz", research_id="research-123")

    # After execution: one image should be generated (the one without RAISE), and one failure logged
    assert isinstance(new_report, str)
    assert len(images) == 1
    img = images[0]
    assert "url" in img and img["url"].startswith("https://images/")
    assert img["section_header"] == "Good Section"
    # generated_images attribute updated on the instance
    assert hasattr(gen, "generated_images")
    assert gen.generated_images == images

    # Verify that the embed function actually added the image markdown in the report
    assert "![alt for A nice diagram]" in new_report
    assert "Good Section" in new_report  # comment embed contains section header

    # Check that stream_output was called for start, analyzing, per-image generating, image_generated, error, complete, and generated_images send
    # Extract event names for easier assertions
    event_names = [c["event_name"] for c in stream_calls]
    # must include at least these event names
    assert "image_generation_start" in event_names
    assert "image_generation_analyzing" in event_names
    assert "image_generating" in event_names
    assert "image_generated" in event_names
    assert "image_generation_error" in event_names
    assert "image_generation_complete" in event_names or "image_generation_complete" in event_names
    # Verify that generated_images were sent as JSON payload in the "generated_images" event call
    gen_images_sends = [c for c in stream_calls if c["event_type"] == "generated_images" and c["event_name"] == "inline_images"]
    assert len(gen_images_sends) >= 1
    # The message for inline_images should be JSON serializable list containing url and alt fields
    inline_payload_msg = gen_images_sends[-1]["message"]
    parsed = json.loads(inline_payload_msg)
    assert isinstance(parsed, list)
    assert parsed[0]["url"] == images[0]["url"]
    assert parsed[0]["alt"] == images[0]["alt_text"]
